#!/usr/bin/env python3
"""Exact minimum-visit coverage of a state-transition line graph with free restarts."""

def minimum_visit_plan(state_model):
    transitions=sorted(state_model["transitions"],key=lambda t:t["id"])
    if not transitions: return [],0
    states=sorted(state_model["states"],key=lambda s:s["id"])
    index={s["id"]:i for i,s in enumerate(states)}
    initial=[index[s["id"]] for s in states if s["isInitial"]]
    if not initial: raise ValueError("Coverage requires a legal initial state")
    n=len(states);root=n;source=n+1;sink=n+2;size=n+3;capacity=len(transitions)+n+1
    network=[[] for _ in range(size)];balance=[0]*n;original=[];resets=[];entries=[]
    def add(a,b,cap,cost):
        forward={"to":b,"rev":len(network[b])+(1 if a==b else 0),"cap":cap,"cost":cost,"initial":cap}
        reverse={"to":a,"rev":len(network[a]),"cap":0,"cost":-cost,"initial":0}
        network[a].append(forward);network[b].append(reverse);return forward
    for t in transitions:
        a=index[t["from"]];b=index[t["to"]];balance[a]+=1;balance[b]-=1
        original.append((a,b,t["id"],add(a,b,capacity,1)))
    for v in range(n): resets.append((v,root,add(v,root,capacity,0)))
    for v in initial: entries.append((root,v,add(root,v,capacity,0)))
    required_flow=0
    for v,b in enumerate(balance):
        if b<0: add(source,v,-b,0);required_flow-=b
        elif b>0: add(v,sink,b,0)
    sent=0;minimum_extra=0
    while sent<required_flow:
        # Bellman-Ford supports negative residual reverse costs. Strict updates fix tie order.
        distance=[float("inf")]*size;distance[source]=0;previous=[None]*size
        for _ in range(size-1):
            changed=False
            for v,arcs in enumerate(network):
                if distance[v]==float("inf"): continue
                for j,arc in enumerate(arcs):
                    if arc["cap"]>0 and distance[arc["to"]]>distance[v]+arc["cost"]:
                        distance[arc["to"]]=distance[v]+arc["cost"];previous[arc["to"]]=(v,j);changed=True
            if not changed: break
        if previous[sink] is None: raise ValueError("No legal route can cover every requirement from the initial states")
        amount=required_flow-sent;v=sink
        while v!=source:
            a,j=previous[v];amount=min(amount,network[a][j]["cap"]);v=a
        v=sink
        while v!=source:
            a,j=previous[v];arc=network[a][j];arc["cap"]-=amount;network[v][arc["rev"]]["cap"]+=amount;v=a
        sent+=amount;minimum_extra+=amount*distance[sink]
    # No negative residual cycle certifies min-cost optimality of the integer flow.
    potential=[0]*(n+1)
    for iteration in range(n+1):
        changed=False
        for v in range(n+1):
            for arc in network[v]:
                if arc["to"]<=root and arc["cap"]>0 and potential[arc["to"]]>potential[v]+arc["cost"]:
                    potential[arc["to"]]=potential[v]+arc["cost"];changed=True
        if not changed: break
        if iteration==n: raise ValueError("Optimizer left a negative residual cycle")
    dual_bound=sum(balance[v]*potential[v] for v in range(n))
    if minimum_extra!=dual_bound: raise ValueError("Flow cost does not attain its dual lower bound")
    support=[[] for _ in range(n+1)]
    def include(a,b,count,transition=None,order=0):
        if count: support[a].append({"to":b,"left":count,"transition":transition,"order":order})
    for a,b,ident,arc in original: include(a,b,1+arc["initial"]-arc["cap"],ident,0)
    for a,b,arc in resets: include(a,b,arc["initial"]-arc["cap"],order=2)
    for a,b,arc in entries: include(a,b,arc["initial"]-arc["cap"],order=1)
    # Each required weak component contains an initial state by upstream reachability.
    # Free balanced connectors join disconnected balanced cycles to one Euler walk.
    for v in initial: include(root,v,1,order=1);include(v,root,1,order=2)
    for arcs in support: arcs.sort(key=lambda a:(a["order"],a["transition"] or "",a["to"]))
    offsets=[0]*(n+1);stack=[(root,None)];reverse=[]
    while stack:
        v,_=stack[-1];arcs=support[v]
        while offsets[v]<len(arcs) and not arcs[offsets[v]]["left"]: offsets[v]+=1
        if offsets[v]<len(arcs):
            arc=arcs[offsets[v]];arc["left"]-=1;stack.append((arc["to"],arc["transition"]))
        else:
            _,ident=stack.pop()
            if ident is not None: reverse.append("R-"+ident)
    if any(arc["left"] for arcs in support for arc in arcs): raise ValueError("Required component is not connected to a legal initial state")
    sequence=list(reversed(reverse));minimum=len(transitions)+minimum_extra
    if len(sequence)!=minimum: raise ValueError("Euler route cost disagrees with the min-cost lower bound")
    return sequence,minimum
