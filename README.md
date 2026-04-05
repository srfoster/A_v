# A_v

For realtime fanciness:

Terminal 1:
python realtime_listen.py input/begin-with-a-circle/begin-with-a-circle.script

Terminal 2:
python run_browser_interpreter.py

---

For vlogging pipeline:

python process_next_video.py

That should run all our various processors on the next unprocessed video (one without logs/), then will run day/ processors on the day, and all/ processors on the full /s/Videos/Raw folder.  The latter are mostly to update the html files for interacting with the various output.


---

Future:

* OCR has been blocked thus far:
  * Easy OCR sucks
  * Paddle OCR, hasn't given results yet
  * And there's a flaw in the basic idea of the ocr_extractions processor -- there are going to be too many thumbs to process (unless paddle is blazingly fast).  We probably need a processor to run first, which would output a short-list of thumbs to extract from -- possibly based on the subtitles (e.g. I say "Let's extract this text", and a thumb is created in to_ocr/)
* Can llama clean up the subtitles?  Try making a processor for this...
  - Is there a better model?