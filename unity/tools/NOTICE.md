# Third-party components in this folder

Self-built tools here are original work (see each tool's source). These
third-party binaries ship inside them:

| Component | Used by | Upstream | License |
|---|---|---|---|
| Mono.Cecil (+ .Mdb, .Pdb, .Rocks) | usdump, uspatch, usref, ldstrdump, ilprobe, ildiff, typescan, herai_ext | https://github.com/jbevain/cecil | MIT |
| AssetsTools.NET (+ Cpp2IL, MonoCecil adapters) | herai_ext | https://github.com/Devoto-Audio/AssetsTools.NET | MIT |
| LibCpp2IL / Cpp2IL | herai_ext | https://github.com/Devoto-Audio/Cpp2IL | MIT |
| WasmDisassembler | herai_ext | https://github.com/Devoto-Audio/WasmDisassembler | MIT |
| IndexRange | herai_ext | part of the AssetsTools.NET stack | MIT |

Verify against upstream before redistributing beyond this repo's license terms.
