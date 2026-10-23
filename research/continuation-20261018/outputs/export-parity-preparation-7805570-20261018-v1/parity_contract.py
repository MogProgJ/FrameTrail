"""Existing RF detection-parity tolerances; no model inference."""
import numpy as np
from scipy.optimize import linear_sum_assignment

def iou(a,b):
    overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap
    return overlap/union if union else 0

def compare(a,b,w,h):
    if len(a)!=len(b):return dict(passed=False,reason='detection-count-differs',expected=len(a),actual=len(b))
    if not a:return dict(passed=True,detections=0)
    costs=np.array([[1-iou(x['box'],y['box']) if x['canonical_id']==y['canonical_id'] else 1000 for y in b] for x in a])
    ai,bi=linear_sum_assignment(costs)
    overlaps=[iou(a[i]['box'],b[j]['box']) for i,j in zip(ai,bi)]
    confidence=max(abs(a[i]['confidence']-b[j]['confidence']) for i,j in zip(ai,bi))
    geometry=max(abs(x-y)/(w if k%2==0 else h) for i,j in zip(ai,bi) for k,(x,y) in enumerate(zip(a[i]['box'],b[j]['box'])))
    classes=all(a[i]['canonical_id']==b[j]['canonical_id'] for i,j in zip(ai,bi))
    return dict(passed=classes and min(overlaps)>=.99 and confidence<=.002 and geometry<=.002,
        detections=len(a),classes_match=classes,minimum_iou=min(overlaps),maximum_confidence_difference=confidence,maximum_normalized_box_difference=geometry)
