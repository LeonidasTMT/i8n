using Mono.Cecil;
// typescan <dir> <typeNameSubstring>: prints fields+methods (with IL instruction counts) of matching types incl. nested
string dir2 = args[0]; string tn = args[1];
foreach (var path in System.IO.Directory.GetFiles(dir2, "*.dll")) { ModuleDefinition mod; try { mod = Mono.Cecil.ModuleDefinition.ReadModule(path); } catch { continue; }
  foreach (var type in mod.GetTypes()) { if (type.Name.Contains(tn)) Print(type); } }
return 0;
static void Print(TypeDefinition t) { Console.WriteLine("TYPE " + t.FullName + (t.BaseType != null ? " : " + t.BaseType.FullName : ""));
  foreach (var f in t.Fields) Console.WriteLine($"  FIELD {f.FieldType.FullName} {f.Name}");
  foreach (var m in t.Methods) Console.WriteLine($"  METHOD {m.Name}({string.Join(",", m.Parameters.Select(p => p.ParameterType.Name))}) -> {m.ReturnType.Name}" + (m.Body != null ? " [" + m.Body.Instructions.Count + "i]" : " [nobody]"));
  foreach (var n in t.NestedTypes) Print(n); }
