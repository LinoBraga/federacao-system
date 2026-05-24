import { useEffect, useState, useMemo } from "react";

export default function App() {
  const [players, setPlayers] = useState([]);
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState("all");

  useEffect(() => {
    const API_URL = "https://fpbx-backend.onrender.com";
    
    // Define a rota baseada no que o usuário selecionou
    // Se for "all" ou "ranking_std", usamos a rota de padrão
    let endpoint = "/ranking/ranking_std";
    
    if (viewMode === "ranking_rapid") endpoint = "/ranking/ranking_rapid";
    if (viewMode === "ranking_blitz") endpoint = "/ranking/ranking_blitz";

    fetch(`${API_URL}${endpoint}`)
      .then(res => {
        if (!res.ok) throw new Error("Erro na rede");
        return res.json();
      })
      .then(data => {
        // SEGURANÇA: Garante que o estado sempre receba um array
        setPlayers(Array.isArray(data) ? data : []);
      })
      .catch(err => {
        console.error("Erro ao buscar ranking:", err);
        setPlayers([]); // Previne o erro "is not iterable" ao zerar o estado
      });
  }, [viewMode]); // Adicionamos [viewMode] para o ranking atualizar ao trocar de aba

  // Função auxiliar para garantir que estamos pegando o valor numérico correto
  const getRating = (player, field) => {
    const val = player[field];
    return (val !== undefined && val !== null && val !== "") ? Number(val) : 1800; // Assume 1800 se nulo
  };

  const visiblePlayers = useMemo(() => {
    // 1. Define a chave de ordenação baseada no modo
    const ratingMap = {
      "ranking_std": "rating_std",
      "ranking_rapid": "rating_rpd",
      "ranking_blitz": "rating_blz"
    };
    const ratingKey = ratingMap[viewMode] || "rating_std";

    // 2. Ordena (do maior para o menor)
    let sorted = [...players].sort((a, b) => {
      return getRating(b, ratingKey) - getRating(a, ratingKey);
    });

    // 3. Filtra por nome
    if (search.trim() !== "") {
      sorted = sorted.filter(p =>
        p.name && p.name.toLowerCase().includes(search.toLowerCase())
      );
    }

    // 4. Gera ranking absoluto (Todos)
    return sorted.map((player, index) => ({
      ...player,
      actualRank: index + 1
    }));
  }, [players, viewMode, search]);

  const renderRankBadge = (rank) => {
    if (rank === 1) return <span style={{ ...styles.badge, background: "#ffd700", color: "#000" }}>1º</span>;
    if (rank === 2) return <span style={{ ...styles.badge, background: "#c0c0c0", color: "#000" }}>2º</span>;
    if (rank === 3) return <span style={{ ...styles.badge, background: "#cd7f32", color: "#fff" }}>3º</span>;
    return <span style={styles.rankText}>#{rank}</span>;
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>Federação Paraibana de Xadrez</h1>
        <div style={styles.subtitle}>Ranking Oficial FPBX</div>
      </header>

      <div style={styles.controlsContainer}>
        <div style={styles.tabs}>
          <button onClick={() => setViewMode("all")} style={{ ...styles.tabButton, ...(viewMode === "all" ? styles.activeTab : {}) }}>Todos</button>
          <button onClick={() => setViewMode("ranking_std")} style={{ ...styles.tabButton, ...(viewMode === "ranking_std" ? styles.activeTab : {}) }}>Standard</button>
          <button onClick={() => setViewMode("ranking_rapid")} style={{ ...styles.tabButton, ...(viewMode === "ranking_rapid" ? styles.activeTab : {}) }}>Rápido</button>
          <button onClick={() => setViewMode("ranking_blitz")} style={{ ...styles.tabButton, ...(viewMode === "ranking_blitz" ? styles.activeTab : {}) }}>Blitz</button>
        </div>

        <input
          placeholder="Buscar enxadrista..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.input}
        />
      </div>

      <main style={styles.leaderboard}>
        {visiblePlayers.length === 0 ? (
          <div style={styles.emptyState}>Nenhum enxadrista encontrado.</div>
        ) : (
          visiblePlayers.map((p) => (
            <div key={p.id} style={styles.playerRow}>
              <div style={styles.playerInfo}>
                <div style={styles.rankContainer}>{renderRankBadge(p.actualRank)}</div>
                <div style={styles.playerName}>{p.name}</div>
              </div>
              <div style={styles.ratingsGroup}>
                <div style={{ ...styles.ratingTag, ...(viewMode === "ranking_std" ? styles.activeRatingTag : {}) }}>
                  <span style={styles.ratingLabel}>STD</span>
                  <span style={styles.ratingValue}>{p.rating_std}</span>
                </div>
                <div style={{ ...styles.ratingTag, ...(viewMode === "ranking_rapid" ? styles.activeRatingTag : {}) }}>
                  <span style={styles.ratingLabel}>RPD</span>
                  <span style={styles.ratingValue}>{p.rating_rpd}</span>
                </div>
                <div style={{ ...styles.ratingTag, ...(viewMode === "ranking_blitz" ? styles.activeRatingTag : {}) }}>
                  <span style={styles.ratingLabel}>BLZ</span>
                  <span style={styles.ratingValue}>{p.rating_blz}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}

const styles = {
  // ... mantenha os outros
  container: { 
    minHeight: "100vh", 
    background: "#08090a", 
    color: "#f1f3f5", 
    padding: "20px 10px", // Reduzi o padding nas laterais para telas pequenas
    display: "flex", 
    flexDirection: "column", 
    alignItems: "center" 
  },
  controlsContainer: { 
    width: "100%", 
    maxWidth: "800px", 
    display: "flex", 
    flexDirection: "column", 
    gap: "10px", 
    marginBottom: "20px" 
  },
  tabs: { 
    display: "flex", 
    background: "#121416", 
    padding: "4px", 
    borderRadius: "8px", 
    border: "1px solid #212529", 
    overflowX: "auto", // Permite rolar os botões se não couberem na tela
    gap: "4px",
    width: "100%"
  },
  tabButton: { 
    flex: "1 0 auto", // Impede que os botões fiquem espremidos
    padding: "10px 12px", 
    fontSize: "13px", 
    // ... restante
  },
  playerRow: { 
    display: "flex", 
    justifyContent: "space-between", 
    alignItems: "center", 
    background: "#121416", 
    padding: "12px", // Menos padding para caber mais info
    borderRadius: "8px", 
    border: "1px solid #1a1d20",
    width: "100%", // Garante que a linha ocupe 100% do espaço disponível
    boxSizing: "border-box" // Essencial para evitar que o padding quebre a largura
  },
  ratingsGroup: { 
    display: "flex", 
    gap: "4px" // Menos espaço entre tags de rating
  },
  ratingTag: { 
    display: "flex", 
    flexDirection: "column", 
    alignItems: "center", 
    padding: "4px 6px", // Tags menores
    minWidth: "45px" // Tags mais estreitas
  }
};