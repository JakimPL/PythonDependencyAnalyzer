import a.b.c
import x.y.z as w
from p.q import r

x  # undefined
x.y  # undefined
x.y.z  # undefined
w  # x.y.z
w.function()  # needs resolving


b  # undefined
c  # undefined
b.c  # undefined
a  # a.b.c
a.d  # a.b.c.d; needs resolving
a.b.d  # a.b.c.b.d; needs resolving
a.function()  # needs resolving

p  # undefined
p.q  # undefined
p.q.r  # undefined
q.r  # undefined
r  # p.q
r.function()  # needs resolving
