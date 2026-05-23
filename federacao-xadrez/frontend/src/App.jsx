import { useEffect, useState, useMemo } from "react";

export default function App() {
  const [players, setPlayers] = useState([]);
  const [search, setSearch] = useState("");
  
  // viewMode: "all", "top10_std", "top10_rapid" ou "top10_blitz"
  const [viewMode, setViewMode] = useState("all");

  useEffect(() => {
    const API_URL = "https://fpbx-backend.onrender.com";

    fetch(`${API_URL}/ranking`)
      .then(res => {
        if (!res.ok) throw new Error("Erro na resposta do servidor");
        return res.json();
      })
      .then(data => {
        // 🔍 Log temporário no console do navegador para você inspecionar a estrutura real que chegou do backend
        if (data && data.length > 0) {
          console.log("Exemplo de jogador vindo da API:", data[0]);
        }
        setPlayers(data);
      })
      .catch(err => console.error("Erro ao buscar ranking:", err));
  }, []);

  // Processa a lista com tratamento rigoroso de tipos (Garante do maior para o menor)
  const visiblePlayers = useMemo(() => {
    let result = [...players];

    // Função auxiliar tolerante que aceita variações de nome de campo (blz vs blitz)
    const getRating = (player, field) => {
      let val = player[field];
      
      // Se estiver procurando blitz e vier nulo, tenta variações comuns
      if (field === "rating_blz" && (val === undefined || val === null)) {
        val = player["rating_blitz"] ?? player["blitz"];
      }
      if (field === "rating_rpd" && (val === undefined || val === null)) {
        val = player["rating_rapid"] ?? player["rapid"];
      }

      return val !== undefined && val !== null ? Number(val) : 0;
    };

    // 1. Ordenação segura do Maior para o Menor (b - a)
    if (viewMode === "top10_rapid") {
      result.sort((a, b) => getRating(b, "rating_rpd") - getRating(a, "rating_rpd"));
    } else if (viewMode === "top10_blitz") {
      result.sort((a, b) => getRating(b, "rating_blz") - getRating(a, "rating_blz"));
    } else {
      result.sort((a, b) => getRating(b, "rating_std") - getRating(a, "rating_std"));
    }

    // 2. Criação do Rank real absoluto pós-ordenação
    let rankedResult = result.map((player, index) => ({
      ...player,
      actualRank: index + 1
    }));

    // 3. Filtro de pesquisa por nome (Protegido contra campos nulos)
    if (search.trim() !== "") {
      rankedResult = rankedResult.filter(p =>
        p.name && p.name.toLowerCase().includes(search.toLowerCase())
      );
    }

    // 4. Corte do Top 10 se não for a aba "Todos"
    if (viewMode !== "all") {
      rankedResult = rankedResult.slice(0, 10);
    }

    return rankedResult;
  }, [players, viewMode, search]);

  // Função auxiliar para renderizar o pódio com elegância
  const renderRankBadge = (rank) => {
    if (rank === 1) return <span style={{ ...styles.badge, background: "#ffd700", color: "#000" }}>1º</span>;
    if (rank === 2) return <span style={{ ...styles.badge, background: "#c0c0c0", color: "#000" }}>2º</span>;
    if (rank === 3) return <span style={{ ...styles.badge, background: "#cd7f32", color: "#fff" }}>3º</span>;
    return <span style={styles.rankText}>#{rank}</span>;
  };

  return (
    <div style={styles.container}>
      
      {/* HEADER */}
      <header style={styles.header}>
        <div style={styles.logoBox}>
          <div style={styles.brandLine}></div>
          <h1 style={styles.title}>Federação Paraibana de Xadrez</h1>
          <div style={styles.subtitle}>Ranking Oficial FPBX</div>
        </div>
      </header>

      {/* CONTROLES / FILTROS */}
      <div style={styles.controlsContainer}>
        <div style={styles.tabs}>
          <button
            onClick={() => setViewMode("all")}
            style={{ ...styles.tabButton, ...(viewMode === "all" ? styles.activeTab : {}) }}
          >
            Todos
          </button>
          <button
            onClick={() => setViewMode("top10_std")}
            style={{ ...styles.tabButton, ...(viewMode === "top10_std" ? styles.activeTab : {}) }}
          >
            Top 10 Standard
          </button>
          <button
            onClick={() => setViewMode("top10_rapid")}
            style={{ ...styles.tabButton, ...(viewMode === "top10_rapid" ? styles.activeTab : {}) }}
          >
            Top 10 Rápido
          </button>
          <button
            onClick={() => setViewMode("top10_blitz")}
            style={{ ...styles.tabButton, ...(viewMode === "top10_blitz" ? styles.activeTab : {}) }}
          >
            Top 10 Blitz
          </button>
        </div>

        <div style={styles.searchBox}>
          <input
            placeholder="Buscar enxadrista..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={styles.input}
          />
        </div>
      </div>

      {/* LISTA / RANKING */}
      <main style={styles.leaderboard}>
        {visiblePlayers.length === 0 ? (
          <div style={styles.emptyState}>Nenhum enxadrista encontrado.</div>
        ) : (
          visiblePlayers.map((p) => {
            const isStdActive = viewMode === "all" || viewMode === "top10_std";
            const isRapidActive = viewMode === "top10_rapid";
            const isBlitzActive = viewMode === "top10_blitz";

            // Encontra o valor do Blitz buscando em chaves alternativas se necessário
            const blitzValue = p.rating_blz ?? p.rating_blitz ?? p.blitz;

            return (
              <div key={`${viewMode}-${p.id || p.actualRank}`} style={styles.playerRow}>
                
                {/* Lado Esquerdo: Posição e Nome */}
                <div style={styles.playerInfo}>
                  <div style={styles.rankContainer}>
                    {renderRankBadge(p.actualRank)}
                  </div>
                  <div style={styles.playerName}>{p.name}</div>
                </div>

                {/* Lado Direito: Bloco de Ratings */}
                <div style={styles.ratingsGroup}>
                  <div style={{ ...styles.ratingTag, ...(isStdActive ? styles.activeRatingTag : {}) }}>
                    <span style={styles.ratingLabel}>STD</span>
                    <span style={styles.ratingValue}>{p.rating_std ?? "—"}</span>
                  </div>
                  <div style={{ ...styles.ratingTag, ...(isRapidActive ? styles.activeRatingTag : {}) }}>
                    <span style={styles.ratingLabel}>RPD</span>
                    <span style={styles.ratingValue}>{p.rating_rpd ?? p.rating_rapid ?? "—"}</span>
                  </div>
                  <div style={{ ...styles.ratingTag, ...(isBlitzActive ? styles.activeRatingTag : {}) }}>
                    <span style={styles.ratingLabel}>BLZ</span>
                    <span style={styles.ratingValue}>
                      {blitzValue !== undefined && blitzValue !== null && blitzValue !== "" ? String(blitzValue) : "—"}
                    </span>
                  </div>
                </div>

              </div>
            );
          })
        )}
      </main>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    background: "#08090a",
    color: "#f1f3f5",
    fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    padding: "40px 20px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center"
  },
  header: { textAlign: "center", marginBottom: "40px" },
  logoBox: { display: "flex", flexDirection: "column", alignItems: "center" },
  brandLine: { width: "60px", height: "4px", background: "#e63946", marginBottom: "16px", borderRadius: "2px" },
  title: { fontSize: "32px", fontWeight: "800", letterSpacing: "-0.5px", margin: "0 0 8px 0", background: "linear-gradient(to right, #ffffff, #a0a0a0)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" },
  subtitle: { color: "#6c757d", fontSize: "15px", fontWeight: "500", textTransform: "uppercase", letterSpacing: "1.5px" },
  controlsContainer: { width: "100%", maxWidth: "800px", display: "flex", flexDirection: "column", gap: "16px", marginBottom: "24px" },
  tabs: { display: "flex", background: "#121416", padding: "4px", borderRadius: "8px", border: "1px solid #212529", overflowX: "auto", gap: "4px" },
  tabButton: { flex: "1", padding: "10px 16px", background: "transparent", border: "none", color: "#adb5bd", fontSize: "14px", fontWeight: "600", borderRadius: "6px", cursor: "pointer", whiteSpace: "nowrap", transition: "all 0.2s ease" },
  activeTab: { background: "#212529", color: "#ffffff", boxShadow: "0 2px 8px rgba(0,0,0,0.2)", border: "1px solid #2b3035" },
  searchBox: { width: "100%" },
  input: { width: "100%", boxSizing: "border-box", padding: "12px 16px", borderRadius: "8px", border: "1px solid #212529", background: "#121416", color: "#ffffff", fontSize: "15px", outline: "none", transition: "border-color 0.2s" },
  leaderboard: { width: "100%", maxWidth: "800px", display: "flex", flexDirection: "column", gap: "8px" },
  playerRow: { display: "flex", justifyContent: "space-between", alignItems: "center", background: "#121416", border: "1px solid #1a1d20", padding: "14px 20px", borderRadius: "8px", transition: "transform 0.15s ease, background-color 0.15s ease", flexWrap: "wrap", gap: "12px" },
  playerInfo: { display: "flex", alignItems: "center", gap: "16px" },
  rankContainer: { width: "40px", display: "flex", justifyContent: "center" },
  rankText: { color: "#6c757d", fontSize: "14px", fontWeight: "700" },
  badge: { padding: "4px 10px", borderRadius: "12px", fontSize: "12px", fontWeight: "bold", boxShadow: "0 2px 4px rgba(0,0,0,0.15)" },
  playerName: { fontSize: "16px", fontWeight: "600", color: "#f8f9fa" },
  ratingsGroup: { display: "flex", gap: "8px" },
  ratingTag: { display: "flex", flexDirection: "column", alignItems: "center", background: "#1a1d20", border: "1px solid #212529", padding: "6px 12px", borderRadius: "6px", minWidth: "65px" },
  activeRatingTag: { background: "rgba(230, 57, 70, 0.1)", borderColor: "#e63946" },
  ratingLabel: { fontSize: "10px", fontWeight: "700", color: "#6c757d", marginBottom: "2px" },
  ratingValue: { fontSize: "13px", fontWeight: "700", color: "#dee2e6" },
  emptyState: { textAlign: "center", padding: "40px", color: "#6c757d", fontSize: "15px" }
};