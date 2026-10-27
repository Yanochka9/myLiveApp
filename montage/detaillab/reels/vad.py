import numpy as np,json
R={'1377':(1.5,5.8),'1380':(0.0,22.2),'1381':(0.0,15.6),'1384':(0.8,11.3),'1387':(0.7,5.3)}
out={}
for n,(a,b) in R.items():
    x=np.frombuffer(open(f'wav/{n}.wav','rb').read()[44:],dtype='int16').astype(float)/32768
    h=320; m=len(x)//h; r=20*np.log10(np.sqrt((x[:m*h].reshape(m,h)**2).mean(1))+1e-9)
    rr=r[r>-100]; floor=np.percentile(rr,10); peak=np.percentile(rr,95); thr=floor+0.35*(peak-floor)
    v=r>thr; t=np.arange(m)*0.02
    segs=[];cur=None
    for i in range(int(a/0.02),min(m,int(b/0.02))):
        if v[i]:
            if cur is None: cur=[t[i],t[i]]
            cur[1]=t[i]+0.02
        elif cur and t[i]-cur[1]>0.28: segs.append(cur);cur=None
    if cur: segs.append(cur)
    segs=[[max(a,s-0.08),min(b,e+0.12)] for s,e in segs if e-s>0.06]
    out[n]=segs
    print(n,f"thr={thr:.0f}",' '.join(f"{s:.2f}-{e:.2f}" for s,e in segs), 'total=%.2f'%sum(e-s for s,e in segs))
json.dump(out,open('segs.json','w'))
