# 📂 Documents Directory

This folder is used by the **RAG Document Ingestion System**.

## How to Use

1. **Place your documents here**: Copy PDFs, Word files (.docx), Excel files (.xlsx), or text files (.txt) into this folder.

2. **Run the ingestion script**:
   ```bash
   python ingest.py
   ```

3. **Start the kiosk**: The assistant will now have knowledge from your documents.
   ```bash
   python main.py
   ```

## Supported Formats

- **PDF** (.pdf) - Hotel manuals, policies, brochures
- **Word** (.docx) - Procedures, FAQs, documentation
- **Excel** (.xlsx, .xls) - Price lists, room availability, schedules
- **Text** (.txt) - Simple notes and information

## Tips

- **Chunk Size**: Large documents are automatically split into 1000-word chunks for better AI processing.
- **Re-ingestion**: You can run `ingest.py` multiple times. New documents will be added to the knowledge base.
- **File Names**: Use descriptive names like `hotel_menu.pdf` or `room_prices.xlsx` for better organization.

## Example Files

Place files like:
- `hotel_policies.pdf`
- `restaurant_menu.docx`
- `room_rates.xlsx`
- `wifi_instructions.txt`
