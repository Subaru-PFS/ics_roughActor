from importlib import reload

import xcuActor.Controllers.gauge as xcuGauge
reload(xcuGauge)

class gauge(xcuGauge.gauge):
    pass

