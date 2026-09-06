const navToggle = document.getElementById("navToggle");
const primaryNav = document.getElementById("primaryNav");
navToggle.addEventListener("click", () => {
  const isOpen = primaryNav.classList.toggle("is-open");
  navToggle.setAttribute("aria-expanded", isOpen);
});

// --- Tự đếm số bài viết theo từng chủ đề (mục "Chủ đề" ở trang chủ) ---
// Đếm trực tiếp trên DOM mỗi lần tải trang, nên không cần sửa tay
// index.html mỗi khi thêm bài mới bằng new_post.py.
const topicItems = document.querySelectorAll(".topic-list li[data-tag]");
topicItems.forEach((li) => {
  const tagClass = li.dataset.tag;
  const count = document.querySelectorAll(
    `.post-grid .post-card .tag.${tagClass}`
  ).length;
  const countEl = li.querySelector(".topic-count");
  if (countEl) countEl.textContent = `${count} bài`;
});

// --- Ô tìm kiếm bài viết (theo tiêu đề, mô tả, chủ đề) ---
// So khớp không phân biệt hoa/thường và có dấu/không dấu.
function boChoTiengViet(str) {
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

const siteSearchInput = document.getElementById("siteSearch");
const searchGrid = document.querySelector(".post-grid.featured-grid");
if (siteSearchInput && searchGrid) {
  const cards = Array.from(searchGrid.querySelectorAll(".post-card"));

  const noResultsEl = document.createElement("p");
  noResultsEl.textContent = "Không tìm thấy bài viết phù hợp.";
  noResultsEl.style.display = "none";
  noResultsEl.style.gridColumn = "1 / -1";
  noResultsEl.style.color = "var(--ink-faint)";
  searchGrid.after(noResultsEl);

  // Lọc danh sách card theo 1 hàm điều kiện (predicate) — dùng chung
  // cho cả gõ tìm kiếm lẫn bấm chọn chủ đề bên dưới.
  function filterCards(predicate) {
    let visibleCount = 0;
    cards.forEach((card) => {
      const isMatch = predicate(card);
      card.style.display = isMatch ? "" : "none";
      if (isMatch) visibleCount += 1;
    });
    noResultsEl.style.display = visibleCount === 0 ? "" : "none";
  }

  siteSearchInput.addEventListener("input", () => {
    const query = boChoTiengViet(siteSearchInput.value.trim());
    filterCards((card) => {
      const title = card.querySelector("h3")?.textContent || "";
      const excerpt = card.querySelector(".excerpt")?.textContent || "";
      const tag = card.querySelector(".tag")?.textContent || "";
      const haystack = boChoTiengViet(`${title} ${excerpt} ${tag}`);
      return haystack.includes(query);
    });
  });

  // --- Bấm vào 1 chủ đề: lọc đúng bài thuộc chủ đề đó ---
  topicItems.forEach((li) => {
    const link = li.querySelector("a");
    if (!link) return;
    link.addEventListener("click", () => {
      const tagClass = li.dataset.tag;
      const topicName = li.querySelector(".topic-name")?.textContent.trim() || "";
      // Hiện tên chủ đề trong ô tìm kiếm để người dùng biết đang lọc
      // theo gì, và có thể gõ đè để quay lại tìm kiếm tự do.
      siteSearchInput.value = topicName;
      filterCards((card) => !!card.querySelector(`.tag.${tagClass}`));
    });
  });
}
