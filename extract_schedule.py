"""Извлечение третьего листа XLSX без изменения оригинала."""
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile


def extract(path):
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as archive:
        strings = [''.join(t.text or '' for t in item.findall('.//m:t', ns))
                   for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', ns)]
        root = ET.fromstring(archive.read('xl/worksheets/sheet3.xml'))
    cells = {}
    for cell in root.findall('m:sheetData/m:row/m:c', ns):
        value = cell.find('m:v', ns)
        if value is not None:
            cells[cell.get('r')] = strings[int(value.text)] if cell.get('t') == 's' else value.text
    assert cells['G3'] == cells['V3'] == 'ИВТ-б-о-242'
    result = {'group': 'ИВТ-б-о-242', 'year': 2026,
              'source': Path(path).name, 'sheet': '3 курс ИВТ ПИ', 'weeks': {}, 'days': {}}
    for parity, heading, kind_col, subject_col in [('even', 'A1', 'F', 'G'), ('odd', 'P1', 'U', 'V')]:
        for date in re.findall(r'\d{2}\.\d{2}', cells[heading]):
            result['weeks'][date] = parity
        result['days'][parity] = {}
        for day in range(6):
            lessons = []
            for number in range(1, 9):
                row = 5 + day * 40 + (number - 1) * 5
                subject = cells.get(f'{subject_col}{row}')
                if not subject:
                    continue
                lessons.append({'number': number, 'subject': subject,
                                'kind': cells.get(f'{kind_col}{row}', 'ПЗ' if subject == 'Системное программирование' else 'не указан'),
                                'teacher': cells.get(f'{subject_col}{row + 1}', ''),
                                'room': cells.get(f'{subject_col}{row + 2}', ''),
                                'note': cells.get(f'{subject_col}{row + 4}', '')})
            result['days'][parity][str(day)] = lessons
    return result


if __name__ == '__main__':
    destination = Path(__file__).with_name('schedule.json')
    destination.write_text(json.dumps(extract(sys.argv[1]), ensure_ascii=False, indent=2))
    print('Расписание сохранено:', destination)
