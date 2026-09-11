/**
 * Code.gs
 * ----------------------------------------------------------------
 * Web app tra cuu PSDS (Pathogen Safety Data Sheet) tu du lieu
 * da import vao Google Sheet (tu file psds_search.csv).
 *
 * Yeu cau Sheet co cac cot (dong 1 la header, dung tu khoa nay):
 *   pathogen | url | section_path | text
 *
 * Cach dung:
 *  1. Tao Google Sheet moi, File > Import > tai len psds_search.csv,
 *     chon "Replace current sheet" hoac import vao 1 sheet rieng.
 *  2. Extensions > Apps Script.
 *  3. Xoa noi dung Code.gs mac dinh, dan toan bo noi dung file nay vao.
 *  4. Tao them 1 file HTML ten "Index" (File > New > HTML), dan noi
 *     dung file Index.html (gui kem) vao.
 *  5. Deploy > New deployment > chon type "Web app":
 *       - Execute as: Me
 *       - Who has access: Anyone (hoac Anyone within [to chuc] neu muon gioi han)
 *  6. Mo URL web app duoc cap -> go/chon ten tac nhan -> xem PSDS.
 * ----------------------------------------------------------------
 */

// Doi ten sheet o day neu ban dat ten khac "Sheet1"
const SHEET_NAME = "Sheet1";

function doGet(e) {
  const template = HtmlService.createTemplateFromFile("Index");
  return template
    .evaluate()
    .setTitle("Tra cuu PSDS")
    .addMetaTag("viewport", "width=device-width, initial-scale=1");
}

/** Doc toan bo du lieu tu Sheet 1 lan, dung chung cho cac ham ben duoi. */
function _readData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sheet) {
    throw new Error(
      'Khong tim thay sheet ten "' + SHEET_NAME + '". Kiem tra lai SHEET_NAME trong Code.gs.'
    );
  }

  const values = sheet.getDataRange().getValues();
  const header = values[0].map(function (h) {
    return String(h).trim().toLowerCase();
  });

  const idxPathogen = header.indexOf("pathogen");
  const idxUrl = header.indexOf("url");
  const idxSection = header.indexOf("section_path");
  const idxText = header.indexOf("text");

  if (idxPathogen === -1 || idxSection === -1 || idxText === -1) {
    throw new Error(
      "Sheet phai co cac cot: pathogen, url, section_path, text (dong dau tien la header)."
    );
  }

  const rows = [];
  for (let i = 1; i < values.length; i++) {
    const row = values[i];
    if (!row[idxPathogen]) continue; // bo qua dong trong
    rows.push({
      pathogen: String(row[idxPathogen]),
      url: idxUrl !== -1 ? String(row[idxUrl]) : "",
      section_path: String(row[idxSection]),
      text: String(row[idxText]),
    });
  }

  return rows;
}

/**
 * Tra ve danh sach ten tac nhan (khong trung), da sap xep A-Z.
 * Duoc goi tu Index.html luc trang web tai xong.
 */
function getPathogenList() {
  const rows = _readData();
  const set = {};
  rows.forEach(function (r) {
    set[r.pathogen] = true;
  });
  return Object.keys(set).sort(function (a, b) {
    return a.localeCompare(b);
  });
}

/**
 * Tra ve toan bo muc (section) cua 1 tac nhan cu the.
 * Duoc goi tu Index.html khi nguoi dung chon/go ten tac nhan.
 *
 * @param {string} pathogenName - ten tac nhan, phai khop chinh xac
 *                                 voi 1 gia tri trong getPathogenList().
 * @return {Object} { url, sections: [{path, text}, ...] }
 */
function getPathogenData(pathogenName) {
  const rows = _readData().filter(function (r) {
    return r.pathogen === pathogenName;
  });

  if (rows.length === 0) {
    return { url: "", sections: [] };
  }

  return {
    url: rows[0].url,
    sections: rows.map(function (r) {
      return { path: r.section_path, text: r.text };
    }),
  };
}
