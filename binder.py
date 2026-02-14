import os
import json

# Folders and output
IMAGE_FOLDER = "images/binder"
OUTPUT_FILE = "binder.html"

# Grab images
images = sorted([
    f for f in os.listdir(IMAGE_FOLDER)
    if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
])

if not images:
    print("No images found in folder.")
    exit()

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Interactive Side-View Binder</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {{
    margin: 0;
    background: #cfcfcf;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    font-family: Arial, sans-serif;
    min-height: 100vh;
}}

.slider-container {{
    width: 90%;
    max-width: 1100px;
    margin-bottom: 10px;
    display: none;
}}

input[type=range] {{
    width: 100%;
}}

.binder-container {{
    perspective: 1500px;
    width: 90%;
    max-width: 1100px;
}}

.binder {{
    width: 100%;
    height: 0;
    padding-bottom: 59.09%;
    position: relative;
    cursor: pointer;
}}

.page {{
    width: 50%;
    height: 100%;
    position: absolute;
    top: 0;
    background: rgba(255,255,255,0.95);
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 5px;
    box-shadow: inset 0 0 8px rgba(0,0,0,0.1);
    overflow: hidden;
    opacity: 0;
    transition: opacity 0.5s ease;
    z-index: 10;
}}

.page img {{
    max-width: 95%;
    max-height: 95%;
    object-fit: contain;
    cursor: zoom-in;
}}

.left-page {{ left: 0; }}
.right-page {{ right: 0; }}

.right-cover {{
    width: 50%;
    height: 100%;
    background: #5a6b7c;
    position: absolute;
    right: 0;
    top: 0;
    border-radius: 5px;
    box-shadow: inset 0 0 10px rgba(0,0,0,0.2);
    transform-origin: left center;
    transition: transform 1s ease, z-index 0s 1s;
    z-index: 20;
}}

.right-cover.open {{
    transform: rotateY(180deg);
    z-index: 0;
}}

.ring {{
    width: 2.2%;
    max-width: 24px;
    aspect-ratio: 1/1;
    border-radius: 50%;
    border: 4px solid silver;
    background: radial-gradient(circle at 40% 40%, #eee 0%, #999 100%);
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    box-shadow: inset 0 2px 5px rgba(255,255,255,0.5),
                0 2px 4px rgba(0,0,0,0.3);
    opacity: 0;
    transition: opacity 0.5s ease 0.5s;
    z-index: 15;
}}

.ring1 {{ top: 20.1%; }}
.ring2 {{ top: 47.7%; }}
.ring3 {{ top: 75.3%; }}

.controls {{
    text-align: center;
    display: none;
    width: 90%;
    max-width: 1100px;
    margin-top: 8px;
}}

button {{
    padding: 10px 15px;
    margin: 0 5px;
    border: none;
    border-radius: 6px;
    background: #333;
    color: white;
    cursor: pointer;
}}

button:hover {{
    background: #555;
}}

.page-info {{
    margin-top: 8px;
    font-size: 12px;
    color: #333;
}}

#fullscreenOverlay {{
    position: fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background: rgba(0,0,0,0.9);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}}

#fullscreenOverlay img {{
    max-width: 95%;
    max-height: 95%;
    object-fit: contain;
}}
</style>
</head>
<body>

<div class="slider-container">
    <input type="range" id="pageSlider" min="0" max="{max(len(images)-2,0)}" step="1">
</div>

<div class="binder-container">
    <div id="binder" class="binder">
        <div class="page left-page">
            <img id="leftPage">
        </div>
        <div class="page right-page">
            <img id="rightPage">
        </div>
        <div id="rightCover" class="right-cover"></div>
        <div class="ring ring1"></div>
        <div class="ring ring2"></div>
        <div class="ring ring3"></div>
    </div>
</div>

<div class="controls">
    <button onclick="prevSpread()">Prev</button>
    <button onclick="nextSpread()">Next</button>
    <div class="page-info" id="pageInfo"></div>
</div>

<div id="fullscreenOverlay"><img id="fullscreenImg"></div>

<script>
var images = {json.dumps(images)};
var basePath = "{IMAGE_FOLDER}/";

var currentIndex = 1;
var firstSpread = true;

var leftPage = document.getElementById("leftPage");
var rightPage = document.getElementById("rightPage");
var pageInfo = document.getElementById("pageInfo");
var slider = document.getElementById("pageSlider");
var rightCover = document.getElementById("rightCover");
var controls = document.querySelector(".controls");
var sliderContainer = document.querySelector(".slider-container");

var leftPageDiv = document.querySelector(".left-page");
var rightPageDiv = document.querySelector(".right-page");

var pages = document.querySelectorAll(".page");
var rings = document.querySelectorAll(".ring");

var fullscreenOverlay = document.getElementById("fullscreenOverlay");
var fullscreenImg = document.getElementById("fullscreenImg");

function renderSpread() {{
    if (firstSpread) {{
        leftPage.src = "";
        rightPage.src = images[0] ? basePath + images[0] : "";
        pageInfo.textContent = "Page 1 of " + images.length;
        slider.value = 0;
    }} else {{
        leftPage.src = images[currentIndex] ? basePath + images[currentIndex] : "";
        rightPage.src = images[currentIndex + 1] ? basePath + images[currentIndex + 1] : "";
        pageInfo.textContent = "Pages " + (currentIndex + 1) + "-" + Math.min(currentIndex + 2, images.length) + " of " + images.length;
        slider.value = currentIndex;
    }}
}}

function nextSpread() {{
    if (firstSpread) {{
        firstSpread = false;
        currentIndex = 1;

        // Reveal both pages now
        leftPageDiv.style.opacity = 1;
        rightPageDiv.style.opacity = 1;

        renderSpread();
        return;
    }}

    if (currentIndex + 2 < images.length) {{
        currentIndex += 2;
        renderSpread();
    }}
}}

function prevSpread() {{
    if (!firstSpread && currentIndex - 2 < 1) {{
        firstSpread = true;

        // Hide left page again
        leftPageDiv.style.opacity = 0;
        rightPageDiv.style.opacity = 1;

        renderSpread();
        return;
    }}

    if (currentIndex - 2 >= 1) {{
        currentIndex -= 2;
        renderSpread();
    }}
}}

slider.addEventListener("input", function() {{
    var val = parseInt(slider.value);

    if (val === 0) {{
        firstSpread = true;
        leftPageDiv.style.opacity = 0;
        rightPageDiv.style.opacity = 1;
    }} else {{
        firstSpread = false;
        currentIndex = val;
        leftPageDiv.style.opacity = 1;
        rightPageDiv.style.opacity = 1;
    }}

    renderSpread();
}});

rightCover.addEventListener("click", function(e) {{
    rightCover.classList.add("open");

    // Only show right page initially
    rightPageDiv.style.opacity = 1;
    leftPageDiv.style.opacity = 0;

    rings.forEach(r => r.style.opacity = 1);
    controls.style.display = "block";
    sliderContainer.style.display = "block";

    firstSpread = true;
    renderSpread();
    e.stopPropagation();
}});

document.addEventListener("keydown", function(e) {{
    if (e.key === "ArrowRight") nextSpread();
    if (e.key === "ArrowLeft") prevSpread();
}});

// Fullscreen
function toggleFullscreen(src) {{
    fullscreenImg.src = src;
    fullscreenOverlay.style.display = "flex";
}}

pages.forEach(page => {{
    page.addEventListener("click", function(e) {{
        var img = page.querySelector("img");
        if (img && img.src) toggleFullscreen(img.src);
        e.stopPropagation();
    }});
}});

fullscreenOverlay.addEventListener("click", function() {{
    fullscreenOverlay.style.display = "none";
}});
</script>

</body>
</html>
"""

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Interactive binder generated: {OUTPUT_FILE}")
