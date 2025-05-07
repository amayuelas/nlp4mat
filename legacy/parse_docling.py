from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions,AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.settings import settings


source = "data_test/2412.14773.pdf"  # document per local path or UR

# accelerator_options = AcceleratorOptions(
#         num_threads=8, device=AcceleratorDevice.CPU
#     )
accelerator_options = AcceleratorOptions(
        num_threads=8, device=AcceleratorDevice.CUDA
)

# Configure pipeline options with formula enrichment
pipeline_options = PdfPipelineOptions()
# pipeline_options.accelerator_options = accelerator_options
pipeline_options.do_formula_enrichment = True
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True

# Initialize converter with format options
converter = DocumentConverter(format_options={
    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
})
settings.debug.profile_pipeline_timings = True

result = converter.convert(source)
# print(result.document.export_to_markdown())  # output: "## Docling Technical Report[...]"

doc_conversion_secs = result.timings["pipeline_total"].times
print(f"Conversion secs: {doc_conversion_secs}")

with open('result.md', 'w') as f:
    f.write(result.document.export_to_markdown())

