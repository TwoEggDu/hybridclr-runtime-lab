using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;
var opcodes=typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static).Where(f=>f.FieldType==typeof(OpCode)).Select(f=>(OpCode)f.GetValue(null)!).ToDictionary(o=>unchecked((ushort)o.Value));
var output=new List<object>();
foreach(var path in args){
 using var stream=File.OpenRead(path);string sha=Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();stream.Position=0;
 using var pe=new PEReader(stream);var md=pe.GetMetadataReader();var types=new List<object>();
 foreach(var h in md.TypeDefinitions){
  var t=md.GetTypeDefinition(h);string ns=md.GetString(t.Namespace),name=md.GetString(t.Name);
  if(ns!="AotConcurrent" && ns!="HotConcurrent")continue;
  string Identity(EntityHandle eh){
   if(eh.IsNil)return "";
   if(eh.Kind==HandleKind.TypeReference){var x=md.GetTypeReference((TypeReferenceHandle)eh);return md.GetString(x.Namespace)+"."+md.GetString(x.Name);}
   if(eh.Kind==HandleKind.TypeDefinition){var x=md.GetTypeDefinition((TypeDefinitionHandle)eh);return md.GetString(x.Namespace)+"."+md.GetString(x.Name);}
   if(eh.Kind==HandleKind.MethodDefinition){var x=md.GetMethodDefinition((MethodDefinitionHandle)eh);return Identity(x.GetDeclaringType())+"::"+md.GetString(x.Name);}
   if(eh.Kind==HandleKind.MemberReference){var x=md.GetMemberReference((MemberReferenceHandle)eh);return Identity(x.Parent)+"::"+md.GetString(x.Name);}
   return eh.Kind+":0x"+MetadataTokens.GetToken(eh).ToString("X8");
  }
  var methods=new List<object>();
  foreach(var mh in t.GetMethods()){
   var m=md.GetMethodDefinition(mh);string mn=md.GetString(m.Name);byte[] il=m.RelativeVirtualAddress==0?Array.Empty<byte>():pe.GetMethodBody(m.RelativeVirtualAddress).GetILBytes()!;
   var calls=new List<object>();
   for(int offset=0;offset<il.Length;){
    int start=offset;ushort code=il[offset++];if(code==0xfe)code=(ushort)(0xfe00|il[offset++]);var op=opcodes[code];
    int size=op.OperandType switch {OperandType.InlineNone=>0,OperandType.ShortInlineI or OperandType.ShortInlineVar or OperandType.ShortInlineBrTarget=>1,OperandType.InlineVar=>2,OperandType.InlineI8 or OperandType.InlineR=>8,OperandType.InlineSwitch=>4+4*BitConverter.ToInt32(il,offset),_=>4};
    if(op.OperandType==OperandType.InlineMethod)calls.Add(new{offset=start,opcode=op.Name,target=Identity(MetadataTokens.EntityHandle(BitConverter.ToInt32(il,offset)))});
    offset+=size;
   }
   var regions=m.RelativeVirtualAddress==0?Array.Empty<object>():pe.GetMethodBody(m.RelativeVirtualAddress).ExceptionRegions.Select(e=>(object)new{kind=e.Kind.ToString(),try_start=e.TryOffset,try_length=e.TryLength,handler_start=e.HandlerOffset,handler_length=e.HandlerLength,catch_type=Identity(e.CatchType)}).ToArray();
   methods.Add(new{calls,exception_regions=regions,name=mn,token=MetadataTokens.GetToken(mh),il_sha256=Convert.ToHexString(SHA256.HashData(il)).ToLowerInvariant(),il_bytes=il.Length,il_hex=Convert.ToHexString(il)});
  }
  types.Add(new{ns,name,token=MetadataTokens.GetToken(h),beforefieldinit=(t.Attributes&TypeAttributes.BeforeFieldInit)!=0,methods});
 }
 output.Add(new{file=Path.GetFileName(path),sha256=sha,types});
}
Console.WriteLine(JsonSerializer.Serialize(output,new JsonSerializerOptions{WriteIndented=true}));
