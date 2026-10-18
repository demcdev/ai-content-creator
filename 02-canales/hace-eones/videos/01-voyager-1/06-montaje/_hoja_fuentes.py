import os
import video01 as v
from PIL import Image
fam = os.environ.get('HE_FUENTE', 'inter')
ts = [v.t_nuevo(103.5), v.t_nuevo(700.0), 14.0]
sh = Image.new('RGB', (3 * 960, 540))
for i, t in enumerate(ts):
    sh.paste(v.fotograma(t).resize((960, 540), Image.LANCZOS), (i * 960, 0))
sh.save('salida/prueba/fuente_%s.png' % fam)
