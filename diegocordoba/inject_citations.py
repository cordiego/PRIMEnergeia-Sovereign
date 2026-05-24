import docx
import os

files_to_update = [
    {
        "path": "Granas/PRIMEnergeia Hydrogen-Compatible Back Contact.docx",
        "citation": "\n\n--- AUTO-INJECTED CITATION (from PRIME OpenAlex mapping) ---\nChen et al. (2019) - Mass production of industrial tunnel oxide passivated contacts (i-TOPCon) silicon solar cells. (10.1002/pip.3180)\nContext: Anchors the discussion of the defect-engineered carbon framework and single-site Molybdenum back contact to the established industrial standard for bifacial n-type substrates."
    },
    {
        "path": "PRIMEnergeia S.a.S. /PRIMEnergeia Granas™/PRIMEnergeia Granas /Granas/White Paper Oficial/Enhanced Near-Infrared Spectral Responsivity in Silicon Bottom Cells via Optimized Tunnel Oxide Passivated Contact (TOPCon) Architectures- A Theoretical and Empirical Analysis for PRIMEnergeia Granas.docx",
        "citation": "\n\n--- AUTO-INJECTED CITATION (from PRIME OpenAlex mapping) ---\nChen et al. (2019) - 24.58% total area efficiency of large-area n-type silicon solar cells with passivating contacts. (10.1016/j.solmat.2019.110258)\nContext: Must be cited explicitly as the 'Reference TOPCon' industrial baseline establishing the 24.58% efficiency ceiling."
    },
    {
        "path": "PRIMEnergeia S.a.S. /PRIMEnergeia Granas™/Material Properties/Encapsulating Excellence Advanced Barrier and Protective Layer Strategies for Granas Panels/Encapsulating Excellence- Advanced Barrier and Protective Layer Strategies for Granas Panels.docx",
        "citation": "\n\n--- AUTO-INJECTED CITATION (from PRIME OpenAlex mapping) ---\n1. Jošt et al. (2020) - Monolithic Perovskite Tandem: Toward 30% Efficiency. (10.1002/aenm.201904102)\n2. Lin et al. (2019) - All-perovskite tandem solar cells with 24.8% efficiency. (10.1038/s41560-019-0466-3)\nContext: Establishes theoretical ~30% ceiling and stringent WVTR/oxygen barrier constraints for suppressing Sn(II) oxidation."
    },
    {
        "path": "PRIMEnergeia S.a.S. /To Do/Carbon Fiber Substrate- Torayca® T700S 12K .docx",
        "citation": "\n\n--- AUTO-INJECTED CITATION (from PRIME OpenAlex mapping) ---\nChen et al. (2019) - Mass production of industrial tunnel oxide passivated contacts (i-TOPCon) silicon solar cells. (10.1002/pip.3180)\nContext: Provides mass-production module baselines against which the CFRP substrate's >1.2 GPa compressive strength must be juxtaposed."
    }
]

for item in files_to_update:
    path = item["path"]
    if os.path.exists(path):
        try:
            doc = docx.Document(path)
            doc.add_paragraph(item["citation"])
            doc.save(path)
            print(f"Successfully injected citation into: {path}")
        except Exception as e:
            print(f"Failed to process {path}: {e}")
    else:
        print(f"File not found: {path}")
