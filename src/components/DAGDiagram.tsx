// DAG Red Bayesiana — organizador gráfico SVG nativo, responsivo, sin perder resolución.
// 7 nodos, 6 aristas, 3 niveles (Pinto Páez 2026, Script 07)

export default function DAGDiagram() {
  // Layout: columnas 0,1,2,3 (izq-der), filas 0,1,2,3 (arriba-abajo)
  // Nodos raíz en columna 0; Peligro_* intermedios que colapsan en col 1 (Peligro);
  // Exposicion y Susceptibilidad en col 1; Riesgo en col 2.
  // SVG viewBox 960x440
  const W = 960, H = 440;
  const stroke = "#4A5568";
  const nodes = [
    { id: "PD", x: 60, y: 80, w: 180, h: 60, label: "Peligro · Déficit", sub: "P − ET₀", color: "#2166AC", text: "#fff" },
    { id: "PT", x: 60, y: 180, w: 180, h: 60, label: "Peligro · Térmico", sub: "Días estrés cultivo", color: "#67A9CF", text: "#fff" },
    { id: "PS", x: 60, y: 280, w: 180, h: 60, label: "Peligro · Sequía", sub: "CDD · 7 / 15 d", color: "#0F4C81", text: "#fff" },
    { id: "P",  x: 340, y: 180, w: 200, h: 70, label: "Peligro", sub: "Regla de daño máximo", color: "#6B4E9B", text: "#fff" },
    { id: "EX", x: 340, y: 60,  w: 200, h: 60, label: "Exposición", sub: "Superficie agrícola (ha)", color: "#228B6E", text: "#fff" },
    { id: "SU", x: 340, y: 300, w: 200, h: 60, label: "Susceptibilidad agroclimática", sub: "1 − aptitud RF", color: "#EF8A62", text: "#fff" },
    { id: "R",  x: 650, y: 175, w: 250, h: 90, label: "Riesgo (IR)", sub: "0·P(Bajo) + 0.5·P(Medio) + 1·P(Alto)", color: "#B2182B", text: "#fff" },
  ];
  const edges = [
    ["PD", "P"], ["PT", "P"], ["PS", "P"],
    ["P", "R"], ["EX", "R"], ["SU", "R"],
  ];

  const byId: Record<string, typeof nodes[number]> = Object.fromEntries(nodes.map(n => [n.id, n]));

  const edgePath = (a: string, b: string) => {
    const A = byId[a], B = byId[b];
    const x1 = A.x + A.w, y1 = A.y + A.h / 2;
    const x2 = B.x,        y2 = B.y + B.h / 2;
    const cx = (x1 + x2) / 2;
    return `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`;
  };

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} xmlns="http://www.w3.org/2000/svg" className="w-full h-auto" aria-label="DAG Red Bayesiana">
        <defs>
          <marker id="arrow" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
            <path d="M 0 0 L 12 6 L 0 12 z" fill={stroke}/>
          </marker>
        </defs>
        {/* Columnas etiquetas */}
        <text x={150} y={28} textAnchor="middle" fill="#4A5568" fontSize="11" fontWeight="700">Nodos raíz</text>
        <text x={440} y={28} textAnchor="middle" fill="#4A5568" fontSize="11" fontWeight="700">Nivel intermedio</text>
        <text x={775} y={28} textAnchor="middle" fill="#4A5568" fontSize="11" fontWeight="700">Nodo objetivo</text>

        {/* Aristas */}
        {edges.map(([a, b], i) => (
          <path key={i} d={edgePath(a, b)} stroke={stroke} strokeWidth="2" fill="none" markerEnd="url(#arrow)"/>
        ))}

        {/* Nodos */}
        {nodes.map(n => (
          <g key={n.id}>
            <rect x={n.x} y={n.y} width={n.w} height={n.h} rx="10" ry="10" fill={n.color} stroke="rgba(0,0,0,0.15)" strokeWidth="1"/>
            <text x={n.x + n.w/2} y={n.y + n.h/2 - 3} textAnchor="middle" fill={n.text} fontSize="14" fontWeight="700">{n.label}</text>
            <text x={n.x + n.w/2} y={n.y + n.h/2 + 15} textAnchor="middle" fill={n.text} fontSize="11" opacity="0.9">{n.sub}</text>
          </g>
        ))}

        {/* IR = ... */}
        <text x={W-20} y={H-12} textAnchor="end" fill="#718096" fontSize="10">
          IR ∈ [0,1] · 1.512 inferencias (42 parroquias × 4 cultivos × 3 SSP × 3 horizontes)
        </text>
      </svg>
    </div>
  );
}
