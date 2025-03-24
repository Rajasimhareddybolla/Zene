import openai
import base64
import json
import asyncio
import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict
from rich.console import Console
import dotenv
app = FastAPI()
dotenv.load_dotenv()
import os
console = Console()
openai_client = openai.Client(api_key=os.getenv("OPENAI_API_KEY")) 

# Create directory for audio files
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

async def generate_tts_stream(text: str, voice: str = "alloy"):
    """Generate speech from text using OpenAI TTS API"""
    try:
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Get audio data from response
        audio_data = response.content
        return audio_data
    except Exception as e:
        console.print(f"[red]Error generating speech: {str(e)}[/red]")
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")

async def save_audio_to_file(audio_data, filename=None):
    """Save audio data to a file and return the filename"""
    if filename is None:
        filename = f"{uuid.uuid4()}.mp3"
    
    filepath = os.path.join(AUDIO_DIR, filename)
    
    # Write the audio data to a file
    with open(filepath, "wb") as f:
        f.write(audio_data)
    
    console.print(f"[green]Saved audio to {filepath}[/green]")
    return filepath

@app.post("/sse-text-to-speech/")
async def sse_text_to_speech(data: List[Dict]):
    """Extract text from new data format and process TTS"""
    # Check if the data is valid
    if not data:
        raise HTTPException(status_code=400, detail="No data provided")
        
    # Extracting text content from nested 'elements' lists
    contents = list(dict.fromkeys(
        [item["content"] for page in data for item in page.get("elements", []) if item.get("type") == "text"]
    ))
    console.print(f"[yellow]Received {len(contents)} items for processing (text only)[/yellow]")

    async def event_generator():
        for index, content in enumerate(contents):
            if not content.strip():
                continue
                
            console.print(f"[cyan]Processing item {index+1}/{len(contents)}[/cyan]")
            try:
                audio_data = await generate_tts_stream(content)
                
                # Save the audio file
                audio_filename = f"segment_{index}_{uuid.uuid4().hex[:8]}.mp3"
                filepath = await save_audio_to_file(audio_data, audio_filename)
                
                # Include file path in the response for the client to play
                b64_audio = base64.b64encode(audio_data).decode('utf-8')
                event_data = {
                    "index": index, 
                    "audio": b64_audio,
                    "filepath": filepath
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                # Small delay to ensure client can process
                await asyncio.sleep(0.1)
            except Exception as e:
                console.print(f"[red]Error processing item {index+1}: {str(e)}[/red]")
                error_data = {"index": index, "error": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/generate-audio/")
async def generate_audio(data: Dict):
    """Generate audio from text and return the file path"""
    text = data.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    voice = data.get("voice", "alloy")
    
    try:
        audio_data = await generate_tts_stream(text, voice)
        
        # Save to file with a unique name
        audio_filename = f"speech_{uuid.uuid4().hex[:8]}.mp3"
        filepath = await save_audio_to_file(audio_data, audio_filename)
        
        return JSONResponse({
            "status": "success",
            "filepath": filepath,
            "text": text
        })
    
    except Exception as e:
        console.print(f"[red]Error generating audio: {str(e)}[/red]")
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "voice-tts"}
