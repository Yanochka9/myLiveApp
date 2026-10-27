import json,sys
from faster_whisper import WhisperModel
m=WhisperModel(sys.argv[1],device="cpu",compute_type="int8")
out={}
for n in sys.argv[2:]:
    segs,_=m.transcribe(__import__("numpy").frombuffer(open(f"wav/{n}.wav","rb").read()[44:],dtype="int16").astype("float32")/32768,language="ru",word_timestamps=True,vad_filter=False,beam_size=5)
    words=[]
    for s in segs:
        for w in s.words: words.append([round(w.start,2),round(w.end,2),w.word.strip(),round(w.probability,2)])
    out[n]=words
    print(f"== {n}: "+" ".join(f"[{w[0]}]{w[2]}" for w in words),flush=True)
json.dump(out,open(f"words_{sys.argv[1]}.json","w"),ensure_ascii=False)
