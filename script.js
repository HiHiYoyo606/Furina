const rowNumber = 4;

async function loadSongList(tag) {
  const loader = document.getElementById('loader');
  const playlist = document.getElementById('playlist');

  loader.style.display = 'block';
  playlist.innerHTML = ''; // 清空原有內容

  try {
    const response = await fetch(`${tag}songs.txt`)
    const text = await response.text();
    const lastModified = response.headers.get("Last-Modified");

    if (lastModified) {
      const date = new Date(lastModified);
      const formatted = date.toLocaleString('sv-SE').replace(' ', ' | Last update: ');
      document.getElementById('last-updated').textContent = `最後更新時間 | ${formatted}`;
    } else {
      document.getElementById('last-updated').textContent = "最後更新時間 | 無法取得";
    }
    const songs = text.split('\n').map(line => line.trim()).filter(Boolean);

    // 建立表格行，每行 4 首歌
    let row;
    songs.forEach((song, index) => {
      if (index % rowNumber === 0) {
        row = playlist.insertRow();
      }
      const cell = row.insertCell();
      cell.textContent = song;
    });

  } catch (e) {
    const row = playlist.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 4;
    cell.textContent = '無法載入歌單 | Failed to load playlist';
  } finally {
    loader.style.display = 'none';
  }
}

document.getElementById('btn-gi').addEventListener('click', () => loadSongList('gi'));
document.getElementById('btn-hsr').addEventListener('click', () => loadSongList('hsr'));