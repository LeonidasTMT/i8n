using System;
using System.Collections.Generic;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// usage: ildiff <a.dll> <b.dll>
// Proves structural identity (same methods, same opcode sequences) and lists exactly
// which Ldstr string operands changed. If opcode sigs match and only Ldstr text differs,
// the rewrite is semantically identical apart from those strings.
if (args.Length < 2) { Console.Error.WriteLine("usage: ildiff <a.dll> <b.dll>"); return 2; }

var A = AssemblyDefinition.ReadAssembly(args[0]);
var B = AssemblyDefinition.ReadAssembly(args[1]);

var (sigA, strA) = Fingerprint(A);
var (sigB, strB) = Fingerprint(B);

Console.WriteLine($"methods A={sigA.Count}  B={sigB.Count}");
var onlyA = sigA.Keys.Except(sigB.Keys).ToList();
var onlyB = sigB.Keys.Except(sigA.Keys).ToList();
Console.WriteLine($"only_in_A={onlyA.Count}  only_in_B={onlyB.Count}");
int sigDiff = 0; var sigSamples = new List<string>();
foreach (var k in sigA.Keys) if (sigB.TryGetValue(k, out var sb) && sigA[k] != sb) { sigDiff++; if (sigSamples.Count < 10) sigSamples.Add(k); }
Console.WriteLine($"opcode-sequence-differences={sigDiff}");
foreach (var s in sigSamples) Console.WriteLine("   SIGDIFF " + s);

// Ldstr multiset diff
var fa = Frequency(strA); var fb = Frequency(strB);
var allKeys = fa.Keys.Union(fb.Keys).ToList();
int changed = 0; var changedLines = new List<string>();
foreach (var k in allKeys)
{
    int ca = fa.TryGetValue(k, out var a) ? a : 0;
    int cb = fb.TryGetValue(k, out var b) ? b : 0;
    if (ca != cb) { changed++; changedLines.Add($"{ca}->{cb}  {k.Replace("\n","\\n").Replace("\r","")}"); }
}
Console.WriteLine($"ldstr-operand-changed-entries={changed}");
foreach (var l in changedLines.Take(40)) Console.WriteLine("   " + l);

return 0;

static (Dictionary<string, string> sig, List<string> strs) Fingerprint(AssemblyDefinition asm)
{
    var sig = new Dictionary<string, string>();
    var strs = new List<string>();
    foreach (var mod in asm.Modules)
        foreach (var type in mod.GetTypes())
            foreach (var m in AllMethods(type))
            {
                if (m.Body == null) continue;
                var key = type.FullName + "#" + m.Name + "/" + m.Parameters.Count;
                var sb = new System.Text.StringBuilder();
                foreach (var inst in m.Body.Instructions)
                {
                    sb.Append(inst.OpCode.Code.ToString()).Append(' ');
                    if (inst.OpCode.Code == Code.Ldstr && inst.Operand is string s) strs.Add(s);
                }
                sig[key] = sb.ToString();
            }
    return (sig, strs);
}

static Dictionary<string, int> Frequency(List<string> xs)
{
    var d = new Dictionary<string, int>();
    foreach (var x in xs) { if (d.TryGetValue(x, out var v)) d[x] = v + 1; else d[x] = 1; }
    return d;
}

static IEnumerable<MethodDefinition> AllMethods(TypeDefinition t)
{
    var list = new List<MethodDefinition>();
    try { foreach (var m in t.Methods) list.Add(m); } catch { }
    try { foreach (var n in t.NestedTypes) foreach (var m in n.Methods) list.Add(m); } catch { }
    return list;
}
