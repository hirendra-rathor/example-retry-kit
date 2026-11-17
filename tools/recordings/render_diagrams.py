"""Render the new proposals from JSON, preserving editable SVG and PNG.

Run with Python 3 and librsvg's rsvg-convert on PATH. These are documentation
tools; Retry Kit itself uses only its committed Python environment.
"""

from html import escape
from pathlib import Path
import json
import subprocess
import textwrap

ASSETS = Path(__file__).resolve().parents[2] / 'docs' / 'milestones' / 'assets'
COLORS = {"new": "#22a06b", "changed": "#3b82f6", "context": "#a3a3a3"}
HEADINGS = ["Domain", "Architecture", "Subsystem Design", "Subsystem Interfaces", "State Management", "Verification"]


def text(x, y, value, size=17, color="#172b3a", weight="normal", anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>'


def start(width, height, title, subtitle, statuses):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
           f'<title>{escape(title)}</title><desc>{escape(subtitle)}</desc>',
           '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="4" orient="auto"><path d="M1,0 L9,4 L1,8" fill="none" stroke="#486578" stroke-width="1.6"/></marker></defs>',
           f'<rect width="{width}" height="{height}" fill="#f5f8fa"/>',
           '<g font-family="Arial, Helvetica, sans-serif">',
           text(32,42,title,28,weight="bold"), text(32,76,subtitle,17)]
    for i,status in enumerate(statuses):
        x=width-320+i*98
        out += [f'<rect x="{x}" y="18" width="90" height="28" rx="5" fill="{COLORS[status]}"/>',text(x+45,38,status,14,"#172b3a" if status=="context" else "white",anchor="middle")]
    return out


def card(out, x,y,w,h,node):
    color=COLORS[node['status']]
    out += [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="#fff" stroke="{color}" stroke-width="2"/>',
            f'<rect x="{x+w-83}" y="{y}" width="83" height="23" rx="3" fill="{color}"/>',
            text(x+w-41.5,y+17,node['status'],13,"#172b3a" if node['status']=="context" else "white",anchor="middle"),
            text(x+15,y+23,node['facet'],14,"#486578")]
    cy=y+52
    for line in textwrap.wrap(node['title'],int((w-30)/10.2)):
        out.append(text(x+15,cy,line,19,weight="bold"));cy+=24
    for paragraph in node['body']:
        color="#596b78" if paragraph.startswith('Today:') else "#172b3a"
        for line in textwrap.wrap(paragraph,int((w-30)/8.6)):
            out.append(text(x+15,cy+3,line,17,color));cy+=22
        cy+=5
    if cy>y+h-5:
        raise ValueError(f'Text overflow in {node["title"]}: {cy-y} > {h-5}')


def arrow(out, points, label, x,y, *, dashed=False):
    out.append(f'<polyline points="{points}" fill="none" stroke="#486578" stroke-width="2" {"stroke-dasharray=\"7 5\"" if dashed else ""} marker-end="url(#arrow)"/>')
    out.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="15" fill="#29485b" style="paint-order:stroke;stroke:#f5f8fa;stroke-width:6px;stroke-linejoin:round">{escape(label)}</text>')


def overview(data):
    rows=max(map(len,data['lanes']))
    width,height=2540,240+rows*302
    out=start(width,height,data['title'],data['subtitle'],['new','changed','context'])
    for col,(heading,nodes) in enumerate(zip(HEADINGS,data['lanes'],strict=True)):
        x=40+col*417
        out.append(f'<rect x="{x-10}" y="103" width="400" height="{height-145}" rx="10" fill="{ "#eaf0f4" if col%2==0 else "#edf3f0"}"/>')
        out.append(text(x+180,138,heading,22,weight="bold",anchor="middle"))
        for row,node in enumerate(nodes):
            card(out,x,170+row*302,370,254,node)
    for row,col,label in data.get('links',[]):
        x=40+col*417;y=170+row*302+254
        arrow(out,f'{x+275},{y} {x+275},{y+27} {x+417+95},{y+27} {x+417+95},{y}',label,x+393,y+20)
    for col,row,label in data.get('vertical',[]):
        x=40+col*417+185;y=170+row*302+254
        arrow(out,f'{x},{y} {x},{y+48}',label,x+92,y+27)
    # Every domain rule explicitly constrains the repeat/admission capability.
    for row in data.get('rule_rows',[2,3,4]):
        sy=170+row*302+126;ty=170+302+126;gx=7+(row-2)*9
        arrow(out,f'40,{sy} {gx},{sy} {gx},{ty} 40,{ty}','',0,0)
    out.append(text(40,height-16,'Domain rule arrows constrain D2. Proposed tests become evidence only after execution; the proposal gives their commands and prerequisites.',16))
    return out


def sequence(data):
    width=40+415*len(data['actors']);height=480+len(data['events'])*76+180
    out=start(width,height,data['title'],data['subtitle'],['new','changed','context'])
    # One process, two distinct ownership boundaries; callback stays caller-owned.
    out += [f'<rect x="420" y="105" width="825" height="{height-210}" rx="13" fill="#eaf1f5" stroke="#94a9b8" stroke-dasharray="7 5"/>',text(440,135,'Retry Kit library boundary — same synchronous Python process',18,weight="bold")]
    positions=[210+i*415 for i in range(len(data['actors']))]
    for x,node in zip(positions,data['actors'],strict=True):
        card(out,x-175,158,350,230,node)
        out.append(f'<path d="M{x} 394 V{height-112}" stroke="#afbec7" stroke-width="1.5" stroke-dasharray="6 6"/>')
    for n,event in enumerate(data['events'],1):
        source,dest,label=event;y=430+(n-1)*76
        x1,x2=positions[source],positions[dest]
        if source==dest:
            arrow(out,f'{x1},{y} {x1+110},{y} {x1+110},{y+27} {x1},{y+27}',f'{n}. {label}',x1+90,y-12)
        else:
            arrow(out,f'{x1},{y} {x2},{y}',f'{n}. {label}',(x1+x2)/2,y-13,dashed=('returns' in label or 'raises' in label))
    for i,line in enumerate(data['notes']):
        out.append(text(40,height-70+i*25,line,17))
    return out


def render(source):
    data=json.loads(source.read_text())
    out=overview(data) if data['kind']=='overview' else sequence(data)
    out.append('</g></svg>')
    svg=source.with_name(source.name.replace('.diagram.json','.svg'))
    svg.write_text('\n'.join(out)+'\n')
    subprocess.run(['rsvg-convert',str(svg),'-o',str(svg.with_suffix('.png'))],check=True)
    print(svg)


if __name__=='__main__':
    for source in sorted(ASSETS.glob('*/*.diagram.json')):
        render(source)
