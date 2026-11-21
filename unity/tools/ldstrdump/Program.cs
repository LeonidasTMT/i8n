using System.Text.Json;
using Mono.Cecil;
using Mono.Cecil.Cil;

// usage: ldstrdump <in.dll> <out.json> [verbose]
// verbose: out.json = array of {v, t, m} (value, type full name, method name)
if (args.Length < 2)
{
    Console.Error.WriteLine("usage: ldstrdump <in.dll> <out.json> [verbose]");
    return 2;
}

bool verbose = args.Length >= 3 && args[2] == "verbose";
var plain = new List<string>();
var rich = new List<(string v, string t, string m)>();
int typesVisited = 0, methodsVisited = 0, instrScanned = 0;

using var asm = AssemblyDefinition.ReadAssembly(args[0]);
foreach (var mod in asm.Modules)
{
    foreach (var type in mod.GetTypes())
    {
        typesVisited++;
        foreach (var m in AllMethods(type))
        {
            if (m.Body == null) continue;
            methodsVisited++;
            foreach (var inst in m.Body.Instructions)
            {
                instrScanned++;
                if (inst.OpCode.Code == Code.Ldstr && inst.Operand is string s)
                {
                    plain.Add(s);
                    rich.Add((s, type.FullName, m.Name));
                }
            }
        }
    }
}

if (verbose)
{
    var arr = rich.Select(r => new { v = r.v, t = r.t, m = r.m }).ToArray();
    File.WriteAllText(args[1], JsonSerializer.Serialize(arr));
}
else
{
    File.WriteAllText(args[1], JsonSerializer.Serialize(plain));
}
Console.Error.WriteLine($"[ldstrdump] literals={plain.Count} types={typesVisited} methods={methodsVisited} instr={instrScanned}");
return 0;

static IEnumerable<MethodDefinition> AllMethods(TypeDefinition t)
{
    var l = new List<MethodDefinition>();
    try { foreach (var m in t.Methods) l.Add(m); } catch { }
    try { foreach (var n in t.NestedTypes) foreach (var m in n.Methods) l.Add(m); } catch { }
    return l;
}
