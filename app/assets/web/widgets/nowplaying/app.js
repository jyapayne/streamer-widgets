const card = document.getElementById("card");
const artWrap = document.getElementById("artWrap");
const artImg = document.getElementById("artImg");
const bubbleContainer = document.getElementById("bubbleContainer");
const bgBubbles = document.getElementById("bgBubbles");
const bgImg  = document.getElementById("bgImg");
const titleEl = document.getElementById("title");
const albumEl = document.getElementById("album");
const artistEl = document.getElementById("artist");
const playingIndicator = document.getElementById("playingIndicator");

let lastKey = "";
let lastTitle = "";
let lastAlbum = "";
let lastArtist = "";

function createBubbles(container, count, scale = 1) {
  if (!container || container.childElementCount > 0) return;
  
  const random = (min, max) => Math.random() * (max - min) + min;

  for (let i = 0; i < count; i++) {
    const bubble = document.createElement("div");
    bubble.classList.add("bubble");

    const size = random(12, 48) * scale;
    const left = random(0, 100);
    const duration = random(9, 18);
    const delay = random(-18, 0);
    const opacity = random(0.4, 0.85);
    const swayDistance = random(-24, 24) * scale;

    bubble.style.width = `${size}px`;
    bubble.style.height = `${size}px`;
    bubble.style.left = `${left}%`;
    bubble.style.animationDuration = `${duration}s`;
    bubble.style.animationDelay = `${delay}s`;
    bubble.style.setProperty("--bubble-opacity", opacity);
    bubble.style.setProperty("--sway-distance", `${swayDistance}px`);

    container.appendChild(bubble);
  }
}

function initBubbles(){
  createBubbles(bubbleContainer, 16, 1);
  createBubbles(bgBubbles, 8, 2.5); // fewer bubbles, scaled up
}

function safeText(s){
  return (s ?? "").toString().trim();
}

function setTextWithMarquee(el, rawValue){
  const content = safeText(rawValue) || "—";

  // Reset to plain text for accurate measurement
  el.classList.remove("marquee");
  el.innerHTML = content;

  const needsMarquee = content !== "—" && el.scrollWidth > el.clientWidth + 2;
  if(needsMarquee){
    el.classList.add("marquee");
    // Calculate duration based on content length for consistent speed
    // e.g., 50px per second
    const width = el.scrollWidth;
    const duration = width / 50; 
    
    el.innerHTML = `<div class="marqueeInner" style="animation-duration:${duration}s"><span>${content}</span><span>${content}</span></div>`;
  }
}

function applyNowPlaying(data){
  try{

    const title = safeText(data.title);
    const album = safeText(data.album);
    const artist = safeText(data.artist);
    const playing = !!data.playing;

    // If nothing is active, hide the card
    const hasAny = title || album || artist;
    if(!hasAny){
      card.classList.add("hidden");
      lastTitle = "";
      lastAlbum = "";
      lastArtist = "";
      return;
    }

    const key = `${title}||${album}||${artist}||${playing}`;

    // Update text with marquee when overflowing
    if(title !== lastTitle){
      setTextWithMarquee(titleEl, title);
      lastTitle = title;
    }
    if(album !== lastAlbum){
      setTextWithMarquee(albumEl, album);
      lastAlbum = album;
    }
    if(artist !== lastArtist){
      setTextWithMarquee(artistEl, artist);
      lastArtist = artist;
    }

    // Update playing indicator
    playingIndicator.classList.add("visible");
    playingIndicator.classList.toggle("paused", !playing);

    const hasArt = !!data.has_art;
    artWrap.classList.toggle("placeholder", !hasArt);
    card.classList.toggle("no-art", !hasArt);
    if(!hasArt){
      initBubbles();
      bgBubbles.classList.remove("hidden");
      bgImg.style.display = "none";
    } else {
      bgBubbles.classList.add("hidden");
      bgImg.style.display = "block";
    }

    // If track changed, swap art with a cache-buster
    if(key !== lastKey){
      const artUrl = `${data.art_url}?v=${data.updated_unix}`;
      artImg.src = artUrl;
      bgImg.src = artUrl;

      // small “pop-in” animation
      card.classList.add("hidden");
      requestAnimationFrame(() => {
        card.classList.remove("hidden");
      });

      lastKey = key;
    } else {
      card.classList.remove("hidden");
    }
  } catch (e){
    // ignore render issues
  }
}

window.addEventListener("resize", () => {
  // Clear cache to force re-evaluation of overflow
  lastTitle = "";
  lastAlbum = "";
  lastArtist = "";
});

let ws = null;
let retryMs = 500;

function wsUrl(){
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/ws`;
}

function connect(){
  try{
    ws = new WebSocket(wsUrl());
  } catch (e){
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    retryMs = 500;
  };

  ws.onmessage = (evt) => {
    try{
      const msg = JSON.parse(evt.data);
      if(msg?.type === "nowplaying"){
        applyNowPlaying(msg.data || {});
      }
    } catch (e){
      // ignore
    }
  };

  ws.onclose = () => scheduleReconnect();
  ws.onerror = () => {
    try{ ws.close(); } catch(e){}
  };
}

function scheduleReconnect(){
  const wait = retryMs;
  retryMs = Math.min(5000, retryMs * 1.5);
  setTimeout(connect, wait);
}

connect();
