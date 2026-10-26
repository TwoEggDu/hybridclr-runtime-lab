# Prefab / AssetBundle resource mounting design

User-approved scope: the 2026-10-26 chat requests an isolated hybridclr-runtime-lab experiment, reuse of the current verified environment, and results in HCLR-4, experiment records and three indexes. Commit/push are separate delivery steps.

Use the locked custom Unity 2022.3.62f3_96770f904ca7, package v9.0.3 / runtime v9.0.1, Windows x64 Development IL2CPP Debug. Create projects/resource-mounting and artifacts/resource-mounting, preserving earlier experiments and the installed Editor.

One self-authored HotUpdate MonoBehaviour has an integer, string, child Transform and TextAsset reference. Compare (1) Assembly.Load plus AddComponent(Type), (2) an inactive Prefab packed into a local AssetBundle, DLL loaded before LoadAsset and Instantiate, (3) separate-process negative controls: DLL absent at resource use, and HotUpdate.dll removed only from the copied Player's startup scripting-assembly list. Include a main-package Resources Prefab as a documented additional comparison.

Record actual type/assembly identity, serialized values/references, Awake/OnEnable/Start/OnDisable/OnDestroy and failure stage. Normal resource fixtures contain number 42, label resource-prefab-v1, child Anchor and payload resource-payload-v1. Code baseline sets number 7 and label code-runtime before activation. Each mode runs in three independent processes. Negative outcomes are observations; an unexpected recovery is investigated rather than rewritten to match the hypothesis.

Three approaches considered: local direct AssetBundle (selected by the user's approved proposal, smallest layer count); Addressables (adds catalogue/provider variables); network-delivered bundles (adds CDN/cache/version routing). This round uses local AssetBundle files and records their hashes. No format migration, external delivery, performance, other platforms or unique internal-runtime-cause claims.

Sources: the fixed package's FilterHotFixAssemblies and PatchScriptingAssemblyList; public HybridCLR MonoBehaviour documentation. Public output contains self-authored sources, text events, manifest summaries and hashes. Runtime sources, binaries, PDB and raw Unity logs remain ignored.
