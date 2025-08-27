// Kích hoạt tìm nhanh cho input có data-tbs-search="#tableId"
(function(){
  const norm = s => (s||"").normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase().trim();
  document.querySelectorAll('[data-tbs-search]').forEach(inp=>{
    const table = document.querySelector(inp.dataset.tbsSearch);
    if(!table || !table.tBodies.length) return;
    const rows = Array.from(table.tBodies[0].rows);
    inp.addEventListener('input', ()=>{
      const q = norm(inp.value);
      rows.forEach(tr=>{
        const text = norm(tr.innerText);
        tr.style.display = (!q || text.includes(q)) ? '' : 'none';
      });
    });
  });
})();
