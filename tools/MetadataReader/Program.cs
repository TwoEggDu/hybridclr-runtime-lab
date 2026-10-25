using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;

// Read metadata and decode instruction boundaries; never load or execute the input DLL.
var opcodes = typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static)
    .Where(f => f.FieldType == typeof(OpCode)).Select(f => (OpCode)f.GetValue(null)!)
    .ToDictionary(op => unchecked((ushort)op.Value));
foreach (var path in args)
{
    using var stream = File.OpenRead(path);
    Console.WriteLine($"FILE {Path.GetFileName(path)} SHA256={Convert.ToHexString(SHA256.HashData(stream))}");
    stream.Position = 0;
    using var pe = new PEReader(stream);
    var reader = pe.GetMetadataReader();
    string Blob(BlobHandle h) => Convert.ToHexString(reader.GetBlobBytes(h));
    string Identity(EntityHandle h)
    {
        switch (h.Kind)
        {
            case HandleKind.TypeReference:
                var tr = reader.GetTypeReference((TypeReferenceHandle)h);
                return Identity(tr.ResolutionScope) + ":" + reader.GetString(tr.Namespace) + "." + reader.GetString(tr.Name);
            case HandleKind.AssemblyReference:
                return reader.GetString(reader.GetAssemblyReference((AssemblyReferenceHandle)h).Name);
            case HandleKind.TypeDefinition:
                var td = reader.GetTypeDefinition((TypeDefinitionHandle)h);
                return reader.GetString(td.Namespace) + "." + reader.GetString(td.Name);
            default: return h.Kind + $"(0x{MetadataTokens.GetToken(h):X8})";
        }
    }
    void PrintOperand(int token)
    {
        var handle = MetadataTokens.EntityHandle(token);
        if (handle.Kind != HandleKind.MethodSpecification) return;
        var spec = reader.GetMethodSpecification((MethodSpecificationHandle)handle);
        var signature = reader.GetBlobReader(spec.Signature);
        var header = signature.ReadByte();
        var count = signature.ReadCompressedInteger();
        var types = new List<string>();
        for (int i = 0; i < count; i++)
        {
            byte type = signature.ReadByte();
            types.Add(type switch
            {
                0x08 => "int32", 0x0e => "string",
                0x11 => "valuetype " + Identity(signature.ReadTypeHandle()),
                _ => throw new NotSupportedException($"Sample decoder: unsupported type 0x{type:X2}")
            });
        }
        if (header != 0x0a || signature.RemainingBytes != 0) throw new BadImageFormatException("Unexpected MethodSpec");
        Console.WriteLine($"  MethodSpec 0x{token:X8} blob={Blob(spec.Signature)} args={string.Join(",", types)}");
        if (spec.Method.Kind == HandleKind.MemberReference)
        {
            var member = reader.GetMemberReference((MemberReferenceHandle)spec.Method);
            Console.WriteLine($"  MemberRef 0x{MetadataTokens.GetToken(spec.Method):X8} {Identity(member.Parent)}::{reader.GetString(member.Name)} sig={Blob(member.Signature)}");
        }
    }
    foreach (var handle in reader.MethodDefinitions)
    {
        var method = reader.GetMethodDefinition(handle);
        var name = reader.GetString(method.Name);
        if (name != "Echo" && !name.StartsWith("Run")) continue;
        Console.WriteLine($"MethodDef 0x{MetadataTokens.GetToken(handle):X8} {Identity(method.GetDeclaringType())}::{name} sig={Blob(method.Signature)}");
        foreach (var gpHandle in method.GetGenericParameters())
        {
            var gp = reader.GetGenericParameter(gpHandle);
            Console.WriteLine($"  GenericParam index={gp.Index} name={reader.GetString(gp.Name)} flags={gp.Attributes} constraints={gp.GetConstraints().Count}");
        }
        if (method.RelativeVirtualAddress == 0) continue;
        var il = pe.GetMethodBody(method.RelativeVirtualAddress).GetILBytes()!;
        for (int offset = 0; offset < il.Length;)
        {
            int start = offset;
            ushort code = il[offset++];
            if (code == 0xfe) code = (ushort)(0xfe00 | il[offset++]);
            var opcode = opcodes[code];
            int size = opcode.OperandType switch
            {
                OperandType.InlineNone => 0,
                OperandType.ShortInlineBrTarget or OperandType.ShortInlineI or OperandType.ShortInlineVar => 1,
                OperandType.InlineVar => 2,
                OperandType.InlineI8 or OperandType.InlineR => 8,
                OperandType.InlineSwitch => checked(4 + 4 * BitConverter.ToInt32(il, offset)),
                _ => 4
            };
            if (offset + size > il.Length) throw new BadImageFormatException("Truncated IL");
            if (opcode.OperandType == OperandType.InlineMethod)
            {
                int token = BitConverter.ToInt32(il, offset);
                Console.WriteLine($"  IL_{start:X4}: {opcode.Name} 0x{token:X8}");
                PrintOperand(token);
            }
            offset += size;
        }
    }
}
