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

* Can llama clean up the srts?  Try making a processor for this...