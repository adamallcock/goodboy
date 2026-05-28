# Goodboy Risk Register

| ID | Risk | Impact | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- | --- |
| R001 | Provider outputs drift as image models update | Regeneration becomes inconsistent | High | Store exact prompts, provider metadata, selected baseline image, and row source images | Open |
| R002 | Codex built-in image generation is not directly callable outside Codex | CLI cannot fully automate that adapter | High | Model it as an interactive Codex adapter with handoff manifests | Open |
| R003 | Chroma-key halos remain visible around fur | Low-quality pet output | High | Keep despill, edge trim, white-background preview, and chroma-edge metric as hard gates | In mitigation |
| R004 | Over-centering removes intentional motion | Animations become stiff | Medium | State-specific anchor policies, stricter idle stabilization, looser motion states, centering report/overlay, and motion-preview QA | In mitigation |
| R005 | Generated frames are near-duplicates | Pet feels static | Medium | Duplicate and perceptual similarity audits plus motion sanity checks | In mitigation |
| R006 | Generated rows contain props, text, shadows, or detached effects | Broken extraction or bad pet behavior | Medium | State specs, avoid rules, component checks, visual QA, and install policy | In mitigation |
| R007 | Credentials leak through manifests or logs | Security issue | Low | Store provider names and key aliases only; never write raw API keys | Open |
| R008 | Google Nano Banana model names change | Adapter breaks | Medium | Use alias mapping and provider capability discovery where available | In mitigation |
| R009 | Petdex package requirements diverge from Codex package requirements | Export friction | Medium | Keep Petdex export as a separate adapter with validation | Open |
| R010 | Human feedback branches become confusing | Lost work or wrong variant installed | Medium | Explicit feedback events and branch manifests | In mitigation |
