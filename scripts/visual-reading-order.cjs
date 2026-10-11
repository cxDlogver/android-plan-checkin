module.exports=(previous,target)=>!!previous&&!!target&&(target.top>=previous.bottom-1||target.left>=previous.right-1&&Math.min(target.bottom,previous.bottom)>Math.max(target.top,previous.top));
