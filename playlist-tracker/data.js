/* Original snapshots, Spotify destinations, and saved-data compatibility. */
const SPOTIFY_PROFILE = "https://open.spotify.com/user/gerald91";
const SPOTIFY_URLS = {
  "Monday's Mixtape": "https://open.spotify.com/playlist/7MmD4cuhVwUE9bXxu7GJxL",
  "Groove": "https://open.spotify.com/playlist/63TcahMoaETS0FKcxC1WQr",
  "Guide to Indie": "https://open.spotify.com/playlist/3U68qj6VyrZ0IoRS1YtbRU",
  "Ancora": "https://open.spotify.com/playlist/4T8pZ3r05sDzB96d36uUjg",
  "Potpourri": "https://open.spotify.com/playlist/5MIWnDQ0hzUx9BzdZW3EIz",
  "Cloudbuster": "https://open.spotify.com/playlist/5QWa4jcRA6j2IXrypbpncK",
  "Broken": "https://open.spotify.com/playlist/3yNhYiEHbAUQDaDGgz6EVa",
  "run": "https://open.spotify.com/playlist/0IWqkVLPaccWkfkCms0hOA",
  "Oddities": "https://open.spotify.com/playlist/3iaHnP4HkGzmah21AworMS",
  "Orpheus": "https://open.spotify.com/playlist/7KJeJONfkK5KzB80hSOeYV",
  "Afterglow": "https://open.spotify.com/playlist/6ZdDGr9f1HAa4gpvyg9VEm",
  "Thirst": "https://open.spotify.com/playlist/4hEn0koYrkTRz0705fGGuK",
  "Vertigo": "https://open.spotify.com/playlist/3MXTvZrxgxTO1iskipHzgL",
  "Masterpiece": "https://open.spotify.com/playlist/5GSh9FFB5Lvp4fAkOQPnlJ",
  "Broadway": "https://open.spotify.com/playlist/5vacDybz55AKcCnVwGk3R9"
};

const DEFAULT_DATA = {
  months: ["Apr 24","May 24","Jun 24","Sep 24","Oct 24","Nov 24","Dec 24","Jan 25","Feb 25","Mar 25","Apr 25","May 25","Jun 25","Jul 25","Aug 25","Sep 25","Oct 25","Nov 25","Dec 25","Jan 26","Feb 26","Mar 26","Apr 26","May 26","Jun 26","Jul 26","Sep 26","Oct 26"],
  playlists: {
    "Monday's Mixtape": [247,250,251,251,307,322,335,361,465,477,488,493,493,492,497,499,501,499,501,503,503,509,511,509,509,510,513,513],
    "Groove": [11,14,14,16,35,55,72,122,140,139,137,136,136,136,136,134,132,132,131,131,132,168,185,193,200,204,218,218],
    "Guide to Indie": [79,85,85,84,86,89,90,96,102,102,102,104,103,104,106,106,107,106,107,107,107,110,111,112,111,111,111,111],
    "Ancora": [21,28,28,28,30,31,31,31,33,32,33,36,34,34,35,36,37,37,37,37,38,38,38,38,38,38,38,38],
    "Thirst": [24,26,26,28,28,28,28,30,30,31,32,32,32,32,32,32,32,32,32,32,33,33,33,34,35,35,35,35],
    "Potpourri": [3,5,5,7,8,8,9,10,24,26,27,29,27,27,28,32,30,30,30,30,31,31,33,32,33,34,34,34],
    "Cloudbuster": [15,19,19,19,18,18,19,21,21,21,21,21,22,22,21,21,21,21,21,21,21,26,29,27,28,28,27,27],
    "Broken": [0,0,0,0,0,0,0,0,0,4,7,8,8,8,7,8,10,11,14,16,19,20,22,22,22,23,23,23],
    "run": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,16,16,16,16,15,15],
    "Oddities": [5,13,14,13,13,13,12,13,13,13,13,13,13,13,13,13,13,13,13,13,13,14,14,14,15,15,15,15],
    "Orpheus": [0,0,0,0,0,0,0,0,0,1,2,3,2,2,4,7,9,9,9,9,10,10,10,10,10,10,10,10],
    "Afterglow": [7,8,8,8,9,9,9,10,10,10,10,10,10,10,9,9,9,9,9,9,9,9,10,9,9,9,9,9],
    "Vertigo": [0,0,0,0,0,0,0,0,0,2,2,3,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6],
    "Masterpiece": [4,4,4,4,4,4,4,5,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6],
    "Broadway": [3,3,3,3,4,4,4,4,4,4,4,4,4,4,4,4,5,5,5,5,5,5,6,5,6,6,6,6]
  }
};

const SNAPSHOT_UPDATED_AT = "Oct 3, 2026";
const STORAGE_KEY = "spotify-tracker-v20";

function cloneDefaultData() {
  return JSON.parse(JSON.stringify(DEFAULT_DATA));
}

function monthLabelToValue(label) {
  const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  if (typeof label !== "string") return null;
  const [month, rawYear] = label.trim().split(/\s+/);
  const monthIdx = MON.indexOf(month);
  const year = Number(rawYear);
  if (monthIdx === -1 || !Number.isFinite(year)) return null;
  const fullYear = year < 100 ? 2000 + year : year;
  return fullYear * 12 + monthIdx;
}

function getMonthLabel(month, year) {
  return `${month} ${String(year).slice(-2)}`;
}

function normalizeData(parsed) {
  const fallback = cloneDefaultData();
  if (!parsed || !Array.isArray(parsed.months) || typeof parsed.playlists !== "object" || !parsed.playlists) {
    return fallback;
  }

  const monthLabels = new Set(DEFAULT_DATA.months);
  parsed.months.forEach(label => {
    if (monthLabelToValue(label) !== null) monthLabels.add(label);
  });
  const months = [...monthLabels].sort((a, b) => monthLabelToValue(a) - monthLabelToValue(b));
  const savedIndexByLabel = new Map();
  parsed.months.forEach((label, index) => {
    if (monthLabelToValue(label) !== null) savedIndexByLabel.set(label, index);
  });
  if (!DEFAULT_DATA.months.every(label => months.includes(label))) return fallback;

  const defaultIndexByLabel = new Map(DEFAULT_DATA.months.map((label, index) => [label, index]));
  const playlists = {};
  Object.keys(DEFAULT_DATA.playlists).forEach(name => {
    const baseline = DEFAULT_DATA.playlists[name];
    const saved = Array.isArray(parsed.playlists[name]) ? parsed.playlists[name] : [];
    const series = [];
    months.forEach((label, index) => {
      const savedIndex = savedIndexByLabel.get(label);
      const candidate = savedIndex === undefined ? NaN : Number(saved[savedIndex]);
      if (Number.isFinite(candidate) && candidate >= 0) {
        series.push(Math.round(candidate));
      } else if (defaultIndexByLabel.has(label)) {
        series.push(baseline[defaultIndexByLabel.get(label)]);
      } else {
        series.push(series[index - 1] ?? baseline[baseline.length - 1] ?? 0);
      }
    });
    playlists[name] = series;
  });

  return { months, playlists };
}

function loadData() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY) || localStorage.getItem("spotify-tracker-v13") || localStorage.getItem("spotify-tracker-v12") || localStorage.getItem("spotify-tracker-v11") || localStorage.getItem("spotify-tracker-v4");
    if (saved) return normalizeData(JSON.parse(saved));
  } catch (error) {
    console.warn("Failed to load saved playlist tracker data", error);
  }
  return cloneDefaultData();
}

function saveData() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}
