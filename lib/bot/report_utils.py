import openpyxl
import os

def generate_excel_report(filename: str, sheet_title: str, data: list):
    """
    Membuat file Excel dari data yang diberikan.
    :param filename: Nama file output.
    :param sheet_title: Judul sheet Excel.
    :param data: Data yang akan ditulis ke dalam Excel.
    :return: Path file yang dibuat.
    """
    try:
        # Buat workbook
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = sheet_title

        # Header kolom
        headers = ["ID", "Judul Komik", "Chapter", "Tipe Komik", "Posisi", "Username", "Reported At"]
        sheet.append(headers)

        # Isi data laporan
        for row in data:
            sheet.append(row)

        # Simpan file
        os.makedirs("reports", exist_ok=True)
        filepath = os.path.join("reports", filename)
        workbook.save(filepath)

        return filepath
    except Exception as e:
        print(f"Error generating Excel report: {e}")
        return None
