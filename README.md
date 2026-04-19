# DevPalette

DevPalette is a fast, interactive color wheel and harmony generator tailored for developers. With its sleek interface, it helps you design, extract, and export beautiful color palettes that fit modern design aesthetics, fully loaded with tools built for your workflow.

## Features

- **Interactive Color Wheel**: Fine-tune your hue, saturation, and lightness using an intuitive HSL wheel. 
- **Extensive Harmony Options**: Easily generate complementary, triadic, analogous, split-complement, tetradic, tints, and shades combinations.
- **Dynamic Contrast Checking**: Instant side-by-side contrast checking against all your saved palette numbers to verify WCAG score passes immediately.
- **AI Palette Generation**: Integration with Ollama allows you to just type a mood or theme (e.g. "tropical sunset", "cyberpunk") and get instant Hex suggestions. 
- **URL Extractor**: Scan any live application URL and DevPalette will pull the top 20 colors directly from its CSS and Javascript links.
- **Full Backend Persistence**: Keep your favorite color sets saved in a persistent backend across your sessions.
- **Developer Export Configs**: Instantly grab the generated palettes and copy them directly as:
    - CSS Variables 
    - Tailwind Config
    - JSON
    - SCSS
    - Hex and HSL Lists

## Tech Stack

- **Frontend**: Vanilla Javascript, HTML5 Canvas, and Vanilla CSS with zero external library bloat.
- **Backend**: Lightweight Python `http.server` designed for fast routing, API handling, and static file delivery.
- **Deployment**: Fully containerized using Docker and Docker Compose. 

## Quick Start

Getting DevPalette running on your local machine takes less than a minute.

### Requirements
- Docker 
- Docker Compose

### Installation

1. Clone this repository.
2. Ensure Docker engine is active.
3. Build and spin up the development container in the background:

```bash
docker compose up -d --build
```

4. Navigate to `http://localhost:8080/` (or whichever port specified in your `.env`/`docker-compose.yml`) to view the application.

## Usage Guide
* **Color Selection**: Click around the wheel or use the sliders for precise manipulation or simply paste a HEX directly. 
* **Harmonies**: Click the icons under "Harmony" to compute immediate complementary values and add them to your palette. 
* **Tab Selection**: Switch between "AI Prompt", "URL Extract", and "Saved" to leverage different generator strategies.
* **Saving**: After saving your palettes into the interface, you can name them with keywords and push them directly to server storage using the "save to server ↑" button. 

## License
MIT
