import { useEffect, useState, useMemo } from "react";

export default function App() {
  const [players, setPlayers] = useState([]);
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState("all");

  useEffect(() => {
    const API_URL = "https://fpbx-backend.onrender.com";

    let endpoint = "/ranking/ranking_std";

    if (viewMode === "ranking_rapid") endpoint = "/ranking/ranking_rapid";
    if (viewMode === "ranking_blitz") endpoint = "/ranking/ranking_blitz";

    fetch(`${API_URL}${endpoint}`)
      .then(res => {
        if (!res.ok) throw new Error("Erro na rede");
        return res.json();
      })
      .then(data => {
        setPlayers(Array.isArray(data) ? data : []);
      })
      .catch(err => {
        console.error("Erro ao buscar ranking:", err);
        setPlayers([]);
      });
  }, [viewMode]);

  const getRating = (player, field) => {
    const val = player[field];
    return val ? Number(val) : 1800;
  };

  const visiblePlayers = useMemo(() => {
    const ratingMap = {
      "ranking_std": "rating_std",
      "ranking_rapid": "rating_rpd",
      "ranking_blitz": "rating_blz"
    };

    const ratingKey =
      viewMode === "all"
        ? "rating_std"
        : ratingMap[viewMode];

    let sorted = [...players].sort((a, b) => {
      return getRating(b, ratingKey) - getRating(a, ratingKey);
    });

    if (search.trim() !== "") {
      sorted = sorted.filter(p =>
        p.name?.toLowerCase().includes(search.toLowerCase())
      );
    }

    return sorted.map((player, index) => ({
      ...player,
      actualRank: index + 1
    }));
  }, [players, viewMode, search]);

  const renderRankBadge = (rank) => {
    if (rank === 1)
      return <span style={{ ...styles.badge, background: "#ffd700", color: "#000" }}>1º</span>;
    if (rank === 2)
      return <span style={{ ...styles.badge, background: "#c0c0c0", color: "#000" }}>2º</span>;
    if (rank === 3)
      return <span style={{ ...styles.badge, background: "#cd7f32", color: "#fff" }}>3º</span>;

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
          <button
            onClick={() => setViewMode("all")}
            style={{
              ...styles.tabButton,
              ...(viewMode === "all" ? styles.activeTab : {})
            }}
          >
            Todos
          </button>

          <button
            onClick={() => setViewMode("ranking_std")}
            style={{
              ...styles.tabButton,
              ...(viewMode === "ranking_std" ? styles.activeTab : {})
            }}
          >
            Standard
          </button>

          <button
            onClick={() => setViewMode("ranking_rapid")}
            style={{
              ...styles.tabButton,
              ...(viewMode === "ranking_rapid" ? styles.activeTab : {})
            }}
          >
            Rápido
          </button>

          <button
            onClick={() => setViewMode("ranking_blitz")}
            style={{
              ...styles.tabButton,
              ...(viewMode === "ranking_blitz" ? styles.activeTab : {})
            }}
          >
            Blitz
          </button>
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
                <div style={styles.rankContainer}>
                  {renderRankBadge(p.actualRank)}
                </div>
                <div style={styles.playerName}>{p.name}</div>
              </div>

              <div style={styles.ratingsGroup}>
                <div
                  style={{
                    ...styles.ratingTag,
                    ...(viewMode === "ranking_std" ? styles.activeRatingTag : {})
                  }}
                >
                  <span style={styles.ratingLabel}>STD</span>
                  <span style={styles.ratingValue}>{p.rating_std}</span>
                </div>

                <div
                  style={{
                    ...styles.ratingTag,
                    ...(viewMode === "ranking_rapid" ? styles.activeRatingTag : {})
                  }}
                >
                  <span style={styles.ratingLabel}>RPD</span>
                  <span style={styles.ratingValue}>{p.rating_rpd}</span>
                </div>

                <div
                  style={{
                    ...styles.ratingTag,
                    ...(viewMode === "ranking_blitz" ? styles.activeRatingTag : {})
                  }}
                >
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
  container: {
    minHeight: "100vh",
    background: "#08090a",
    color: "#f1f3f5",
    padding: "20px 10px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center"
  },

  header: {
    textAlign: "center",
    marginBottom: "20px"
  },

  title: {
    fontSize: "22px",
    fontWeight: "700"
  },

  subtitle: {
    fontSize: "13px",
    color: "#adb5bd"
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
    padding: "6px",
    borderRadius: "10px",
    border: "1px solid #212529",
    gap: "6px"
  },

  tabButton: {
    flex: "1",
    padding: "10px",
    fontSize: "13px",
    background: "transparent",
    border: "1px solid transparent",
    color: "#adb5bd",
    borderRadius: "8px",
    cursor: "pointer",
    transition: "0.2s"
  },

  activeTab: {
    border: "1px solid #ff3b3b",
    background: "#1a1d20",
    color: "#ff3b3b",
    boxShadow: "0 0 10px rgba(255, 59, 59, 0.25)"
  },

  input: {
    padding: "10px",
    borderRadius: "8px",
    border: "1px solid #212529",
    background: "#121416",
    color: "#fff",
    outline: "none"
  },

  leaderboard: {
    width: "100%",
    maxWidth: "800px",
    display: "flex",
    flexDirection: "column",
    gap: "10px"
  },

  playerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    background: "#121416",
    padding: "12px",
    borderRadius: "10px",
    border: "1px solid #1a1d20"
  },

  playerInfo: {
    display: "flex",
    alignItems: "center",
    gap: "10px"
  },

  playerName: {
    fontSize: "14px",
    fontWeight: "500"
  },

  ratingsGroup: {
    display: "flex",
    gap: "6px"
  },

  ratingTag: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "5px 7px",
    borderRadius: "8px",
    border: "1px solid #2a2f33",
    background: "#0f1113",
    minWidth: "50px"
  },

  activeRatingTag: {
    border: "1px solid #ff3b3b",
    background: "#1a1d20",
    color: "#ff3b3b",
    boxShadow: "0 0 8px rgba(255, 59, 59, 0.2)"
  },

  ratingLabel: {
    fontSize: "10px",
    color: "#868e96"
  },

  ratingValue: {
    fontSize: "13px",
    fontWeight: "600"
  },

  rankText: {
    color: "#adb5bd"
  },

  badge: {
    padding: "4px 8px",
    borderRadius: "6px",
    fontSize: "12px",
    fontWeight: "700"
  },

  rankContainer: {
    width: "40px"
  },

  emptyState: {
    textAlign: "center",
    color: "#868e96",
    padding: "20px"
  }
};