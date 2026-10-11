/** Thống kê nhanh bảng điểm: tổng bài, số đã nộp, điểm trung bình (chuỗi 2 chữ số hoặc "–"). */
export function summarizeResults(rows) {
  const scored = rows.filter((r) => r.score !== null);
  const average = scored.length ? (scored.reduce((sum, r) => sum + r.score, 0) / scored.length).toFixed(2) : "–";
  return { total: rows.length, submitted: scored.length, average };
}
