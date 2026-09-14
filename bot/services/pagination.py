def window(current,total, radius=2):
 return range(max(1,current-radius), min(total,current+radius)+1) if total else range(max(1,current-radius),current+radius+1)
