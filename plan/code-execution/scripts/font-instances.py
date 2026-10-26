"""Instantiate the exact canonical variable fonts for runtime native aliases."""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'.cache/font-tools'))
import fontTools
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
out=args.output.resolve();out.relative_to(ROOT.resolve());out.mkdir(parents=True,exist_ok=True)
lib=json.loads((ROOT/'plan/ui-spec/library.json').read_text(encoding='utf-8'))
sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
result={'tool':{'name':'fontTools','version':fontTools.__version__},'instances':[]}
for asset in ('font-noto-sans-sc','font-inter'):
 source=ROOT/'plan/ui-spec'/lib['assets'][asset]['file']
 if sha(source)!=lib['assets'][asset]['sha256']:raise ValueError('Canonical font changed')
 weights=sorted({s['typography']['fontWeight'] for s in lib['styles'].values() if s['typography'] and s['extensions'].get('fontAssetRef')==asset})
 for weight in weights:
  font=TTFont(source,recalcTimestamp=False)
  axes={axis.axisTag:axis.defaultValue for axis in font['fvar'].axes};axes['wght']=weight
  # STAT does not name every supported weight; instance the outlines and
  # explicitly name the static face instead of relying on named STAT values.
  instance=instantiateVariableFont(font,axes,inplace=True,updateFontNames=False)
  style={400:'Regular',600:'SemiBold',700:'Bold'}[weight]
  source_family='Noto Sans SC' if asset=='font-noto-sans-sc' else 'Inter'
  labels={1:source_family,2:style,4:source_family+' '+style,6:source_family.replace(' ','')+'-'+style,16:source_family,17:style}
  for item in instance['name'].names:
   if item.nameID in labels:item.string=labels[item.nameID].encode(item.getEncoding())
  instance['OS/2'].fsSelection=(instance['OS/2'].fsSelection & ~(32|64)) | (32 if weight>=700 else 64 if weight==400 else 0)
  instance['head'].macStyle=(instance['head'].macStyle & ~1) | (1 if weight>=700 else 0)
  if 'fvar' in instance:raise ValueError('Expected a fully static instance')
  family=('NotoSC' if asset=='font-noto-sans-sc' else 'Inter')+str(weight)
  file=out/(('NotoSansSC' if asset=='font-noto-sans-sc' else 'Inter')+'-'+str(weight)+'.ttf')
  instance.save(file)
  if instance['OS/2'].usWeightClass!=weight:raise ValueError('Incorrect native font weight')
  result['instances'].append({'assetRef':asset,'weight':weight,'family':family,'source':{'path':source.relative_to(ROOT).as_posix(),'sha256':sha(source)},'axes':axes,'file':file.name,'sha256':sha(file),'nativeWeightClass':instance['OS/2'].usWeightClass})
  print(f'{family}: {file.stat().st_size} bytes',flush=True)
(out/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
