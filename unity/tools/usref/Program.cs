using System.Reflection;
using Mono.Cecil;
using Mono.Cecil.Cil;

// usage: usref <managedDir> [needle ...]
// scans all *.dll in managedDir, finds methods whose bodies reference user strings
// containing any needle (substring match); prints type+method and a compact IL listing.
if (args.Length < 2) { Console.Error.WriteLine("usage: usref <managedDir> [needle...]"); return 1; }
string dir = args[0];
var needles = new List<string>();
var callNeedles = new List<string>();
foreach (var a in args.Skip(1)) { if (a.StartsWith("call:")) callNeedles.Add(a.Substring(5)); else needles.Add(a); }
bool anyCjkMode = false;

foreach (var path in Directory.GetFiles(dir, "*.dll"))
{
    ModuleDefinition mod;
    try { mod = ModuleDefinition.ReadModule(path); } catch { continue; }

    var matches = new List<(TypeDefinition t, MethodDefinition m, string s)>();
    int cjkMethods = 0;
    foreach (var type in mod.GetTypes())
    {
        foreach (var m in SafeMethods(type))
        {
            if (m.Body == null) continue;
            bool hitCjk = false; bool callHit = false; string callStr = "";
            foreach (var inst in m.Body.Instructions)
            {
                if (inst.OpCode.Code == Code.Ldstr && inst.Operand is string s2)
                {
                    if (needles.Any(n => s2.Contains(n))) { matches.Add((type, m, s2)); callStr = $"string={s2}"; }
                    if (!hitCjk && HasCjk(s2)) hitCjk = true;
                }
                else if ((inst.OpCode.Code == Code.Call || inst.OpCode.Code == Code.Callvirt) && inst.Operand is MethodReference mr2)
                {
                    if (callNeedles.Any(n => mr2.Name.Contains(n))) { callHit = true; callStr = "calls " + (mr2.DeclaringType == null ? "?" : mr2.DeclaringType.FullName) + "." + mr2.Name; }
                }
            }
            if (callHit) matches.Add((type, m, "[call] via " + callStr));
            if (hitCjk) cjkMethods++;
        }
    }
    Console.WriteLine($"== {Path.GetFileName(path)}: matched={matches.Count} cjkLdstrMethods={cjkMethods}");
    foreach (var (t, m, s) in matches.Distinct())
    {
        var ss = s.Replace("\r", "").Replace("\n", "\\n");
        Console.WriteLine("  MATCH string=" + ss);
        Dump(t, m);
    }
}
return 0;

static bool HasCjk(string s)
{
    foreach (var c in s) if ((c >= '\u3000' && c <= '\u9fff') || (c >= '\uf900' && c <= '\ufaff')) return true;
    return false;
}

static IEnumerable<MethodDefinition> SafeMethods(TypeDefinition t)
{
    var list = new List<MethodDefinition>();
    try { foreach (var m in t.Methods) list.Add(m); } catch { }
    try { foreach (var n in t.NestedTypes) foreach (var m in n.Methods) list.Add(m); } catch { }
    return list;
}

static void Dump(TypeDefinition t, MethodDefinition m)
{
    Console.WriteLine($"  TYPE {t.FullName}");
    Console.WriteLine($"  METHOD {m.Name} ({string.Join(", ", m.Parameters.Select(p => p.ParameterType.FullName))}) returns={m.ReturnType.FullName}");
    int n = 0;
    foreach (var inst in m.Body.Instructions)
    {
        if (++n > 400) { Console.WriteLine("    ...(truncated at 400 instrs)"); break; }
        string op = Describe(inst);
        Console.WriteLine($"    {inst.OpCode}: {op}");
    }
}

static string Describe(Instruction inst)
{
    var o = inst.Operand;
    switch (o)
    {
        case null: return "";
        case string s: return $"<{s.Replace("\r","").Replace("\n","\\n")}>";
        case MethodReference mr: return $"{mr.DeclaringType?.FullName ?? "?"}.{mr.Name}({string.Join(",", ParamNames(mr))})";
        case FieldReference fr: return $"{fr.DeclaringType?.FullName ?? "?"}.{fr.Name}";
        case TypeReference tr: return tr.FullName;
        default: return o.ToString() ?? "";
    }
}

static string[] ParamNames(MethodReference mr)
{
    var list = new List<string>();
    try { foreach (var p in mr.Parameters) list.Add(p.ParameterType.FullName); } catch { }
    return list.ToArray();
}
