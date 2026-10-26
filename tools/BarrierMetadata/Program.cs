using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
// Decode only the lab-owned Write methods; never load/execute input assemblies.
var ops=typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static).Where(f=>f.FieldType==typeof(OpCode)).Select(f=>(OpCode)f.GetValue(null)!).ToDictionary(o=>unchecked((ushort)o.Value));
foreach(var path in args){
 using var stream=File.OpenRead(path);Console.WriteLine($"FILE {Path.GetFileName(path)} SHA256={Convert.ToHexString(SHA256.HashData(stream))}");stream.Position=0;
 using var pe=new PEReader(stream);var md=pe.GetMetadataReader();
 string Name(EntityHandle h)=>h.Kind switch {
  HandleKind.TypeDefinition=>md.GetString(md.GetTypeDefinition((TypeDefinitionHandle)h).Name),
  HandleKind.TypeReference=>md.GetString(md.GetTypeReference((TypeReferenceHandle)h).Name),
  HandleKind.FieldDefinition=>md.GetString(md.GetFieldDefinition((FieldDefinitionHandle)h).Name),
  HandleKind.MemberReference=>md.GetString(md.GetMemberReference((MemberReferenceHandle)h).Name),
  HandleKind.MethodDefinition=>md.GetString(md.GetMethodDefinition((MethodDefinitionHandle)h).Name),_=>h.Kind.ToString()};
 foreach(var h in md.MethodDefinitions){var m=md.GetMethodDefinition(h);if(md.GetString(m.Name)!="Write")continue;
  Console.WriteLine($"METHOD {Name(m.GetDeclaringType())}::Write TOKEN={MetadataTokens.GetToken(h):X8}");var il=pe.GetMethodBody(m.RelativeVirtualAddress).GetILBytes()!;
  for(int offset=0;offset<il.Length;){int begin=offset;ushort code=il[offset++];if(code==0xfe)code=(ushort)(0xfe00|il[offset++]);var op=ops[code];int size=op.OperandType switch {
   OperandType.InlineNone=>0,OperandType.ShortInlineBrTarget or OperandType.ShortInlineI or OperandType.ShortInlineVar=>1,OperandType.InlineVar=>2,OperandType.InlineI8 or OperandType.InlineR=>8,OperandType.InlineSwitch=>checked(4+4*BitConverter.ToInt32(il,offset)),_=>4};
   if(offset+size>il.Length)throw new BadImageFormatException("Truncated instruction");
   string operand=Convert.ToHexString(il.AsSpan(offset,size));if(op.OperandType is OperandType.InlineField or OperandType.InlineType or OperandType.InlineMethod or OperandType.InlineTok){int token=BitConverter.ToInt32(il,offset);operand=$"0x{token:X8} {Name(MetadataTokens.EntityHandle(token))}";}
   if(op.OperandType==OperandType.InlineString)operand="string:"+md.GetUserString(MetadataTokens.UserStringHandle(BitConverter.ToInt32(il,offset)&0x00ffffff));
   Console.WriteLine($" IL_{begin:X4}: {op.Name} {operand}");offset+=size;
  }
 }
}
