using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text.Json;
var ops=typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static).Where(x=>x.FieldType==typeof(OpCode)).Select(x=>(OpCode)x.GetValue(null)!).ToDictionary(x=>unchecked((ushort)x.Value));
var output=new List<object>();
foreach(string path in args){
 using var stream=File.OpenRead(path);string hash=Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();stream.Position=0;
 using var pe=new PEReader(stream);var md=pe.GetMetadataReader();var sig=new Names(md);var types=new List<object>();
 string Method(EntityHandle h){
  if(h.Kind==HandleKind.MethodSpecification){var x=md.GetMethodSpecification((MethodSpecificationHandle)h);return Method(x.Method)+"<"+string.Join(",",x.DecodeSignature(sig,null))+">";}
  if(h.Kind==HandleKind.MethodDefinition){var x=md.GetMethodDefinition((MethodDefinitionHandle)h);return sig.Id(x.GetDeclaringType())+"::"+md.GetString(x.Name);}
  if(h.Kind==HandleKind.MemberReference){var x=md.GetMemberReference((MemberReferenceHandle)h);return sig.Id(x.Parent)+"::"+md.GetString(x.Name);}
  return h.Kind.ToString();
 }
 foreach(var th in md.TypeDefinitions){
  var t=md.GetTypeDefinition(th);string full=sig.Id(th);if(!full.StartsWith("AotAsync.")&&!full.StartsWith("HotAsync."))continue;
  var methods=new List<object>();
  foreach(var mh in t.GetMethods()){
   var m=md.GetMethodDefinition(mh);byte[] il=m.RelativeVirtualAddress==0?Array.Empty<byte>():pe.GetMethodBody(m.RelativeVirtualAddress).GetILBytes()!;var calls=new List<object>();
   for(int off=0;off<il.Length;){int start=off;ushort c=il[off++];if(c==0xfe)c=(ushort)(0xfe00|il[off++]);var op=ops[c];int size=op.OperandType switch{OperandType.InlineNone=>0,OperandType.ShortInlineI or OperandType.ShortInlineVar or OperandType.ShortInlineBrTarget=>1,OperandType.InlineVar=>2,OperandType.InlineI8 or OperandType.InlineR=>8,OperandType.InlineSwitch=>4+4*BitConverter.ToInt32(il,off),_=>4};
    if(op.OperandType==OperandType.InlineMethod){int token=BitConverter.ToInt32(il,off);calls.Add(new{offset=start,opcode=op.Name,token,target=Method(MetadataTokens.EntityHandle(token))});}off+=size;
   }
   methods.Add(new{name=md.GetString(m.Name),token=MetadataTokens.GetToken(mh),il_sha256=Convert.ToHexString(SHA256.HashData(il)).ToLowerInvariant(),il_hex=Convert.ToHexString(il),calls});
  }
  types.Add(new{name=full,token=MetadataTokens.GetToken(th),base_type=sig.Id(t.BaseType),fields=t.GetFields().Select(f=>{var x=md.GetFieldDefinition(f);return new{name=md.GetString(x.Name),type=x.DecodeSignature(sig,null)};}).ToArray(),methods});
 }
 output.Add(new{file=Path.GetFileName(path),sha256=hash,assembly=md.GetString(md.GetAssemblyDefinition().Name),references=md.AssemblyReferences.Select(r=>md.GetString(md.GetAssemblyReference(r).Name)).ToArray(),types});
}
Console.WriteLine(JsonSerializer.Serialize(output,new JsonSerializerOptions{WriteIndented=true}));
sealed class Names:ISignatureTypeProvider<string,object?> {
 readonly MetadataReader m;public Names(MetadataReader x){m=x;}
 public string Id(EntityHandle h){if(h.IsNil)return "";if(h.Kind==HandleKind.TypeDefinition){var x=m.GetTypeDefinition((TypeDefinitionHandle)h);return x.GetDeclaringType().IsNil?m.GetString(x.Namespace)+"."+m.GetString(x.Name):Id(x.GetDeclaringType())+"+"+m.GetString(x.Name);}if(h.Kind==HandleKind.TypeReference){var x=m.GetTypeReference((TypeReferenceHandle)h);string scope=x.ResolutionScope.Kind==HandleKind.AssemblyReference?"["+m.GetString(m.GetAssemblyReference((AssemblyReferenceHandle)x.ResolutionScope).Name)+"]":"";return x.ResolutionScope.Kind==HandleKind.TypeReference?Id((TypeReferenceHandle)x.ResolutionScope)+"+"+m.GetString(x.Name):scope+m.GetString(x.Namespace)+"."+m.GetString(x.Name);}if(h.Kind==HandleKind.TypeSpecification)return m.GetTypeSpecification((TypeSpecificationHandle)h).DecodeSignature(this,null);return h.Kind.ToString();}
 public string GetArrayType(string e,ArrayShape s)=>e+"["+s.Rank+"]";
 public string GetByReferenceType(string e)=>e+"&";
 public string GetFunctionPointerType(MethodSignature<string> s)=>"fnptr";
 public string GetGenericInstantiation(string e,ImmutableArray<string> a)=>e+"<"+string.Join(",",a)+">";
 public string GetGenericMethodParameter(object? c,int i)=>"!!"+i;
 public string GetGenericTypeParameter(object? c,int i)=>"!"+i;
 public string GetModifiedType(string m,string u,bool r)=>u;
 public string GetPinnedType(string e)=>e;
 public string GetPointerType(string e)=>e+"*";
 public string GetPrimitiveType(PrimitiveTypeCode c)=>c.ToString();
 public string GetSZArrayType(string e)=>e+"[]";
 public string GetTypeFromDefinition(MetadataReader r,TypeDefinitionHandle h,byte k)=>Id(h);
 public string GetTypeFromReference(MetadataReader r,TypeReferenceHandle h,byte k)=>Id(h);
 public string GetTypeFromSpecification(MetadataReader r,object? c,TypeSpecificationHandle h,byte k)=>Id(h);
}
