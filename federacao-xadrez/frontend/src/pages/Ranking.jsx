import { useEffect, useState } from "react";

export default function Ranking() {
  const [players, setPlayers] = useState([]);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState("std"); // 'std', 'rapid', 'blitz'
  const [topOnly, setTopOnly] = useState(false);

  useEffect(() => {
    // Forçamos o link atual correto diretamente aqui para não depender de variáveis da Vercel
    const API_URL = "https://fpbx-backend.onrender.com";

    fetch(`${API_URL}/ranking`)
      .then(res => {
        if (!res.ok) throw new Error("Erro na resposta do servidor");
        return res.json();
      })
      .then(data => {
        setPlayers(data);
      })
      .catch(err => {
        console.error("Erro ao buscar ranking:", err);
      });
  }, []);

  // 1. Filtra os jogadores pelo sistema de busca por nome
  const filtered = players.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  // 2. Ordena dinamicamente a lista baseada no botão selecionado (STD, RAPID ou BLITZ)
  const sorted = [...filtered].sort((a, b) => {
    if (mode === "rapid") return b.rating_rapid - a.rating_rapid;
    if (mode === "blitz") return b.rating_blitz - a.rating_blitz;
    return b.rating_std - a.rating_std; // Padrão: Standard
  });

  // 3. Limita ao Top 10 se o botão estiver ativo
  const displayed = topOnly ? sorted.slice(0, 10) : sorted;

  // Função auxiliar para mostrar o número correto na tabela de acordo com o modo escolhido
  const getRatingByMode = (player) => {
    if (mode === "rapid") return player.rating_rapid;
    if (mode === "blitz") return player.rating_blitz;
    return player.rating_std;
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🏆 Ranking FPBX</h2>

      {/* CONTROLES */}
      <div style={styles.controls}>
        <input
          placeholder="Buscar jogador..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.input}
        />

        <div style={styles.buttons}>
          <button
            onClick={() => setMode("std")}
            style={mode === "std" ? styles.activeBtn : styles.btn}
          >
            STD
          </button>

          <button
            onClick={() => setMode("rapid")}
            style={mode === "rapid" ? styles.activeBtn : styles.btn}
          >
            RAPID
          </button>

          <button
            onClick={() => setMode("blitz")}
            style={mode === "blitz" ? styles.activeBtn : styles.btn}
          >
            BLITZ
          </button>

          <button
            onClick={() => setTopOnly(!topOnly)}
            style={topOnly ? styles.activeBtn : styles.btn}
          >
            {topOnly ? "MOSTRAR TODOS" : "TOP 10"}
          </button>
        </div>
      </div>

      {/* TABELA */}
      <table style={styles.table}>
        <thead>
          <tr style={styles.headRow}>
            <th style={styles.th}>Pos</th>
            <th style={styles.th_name}>Nome</th>
            <th style={styles.th_rating}>Rating ({mode.toUpperCase()})</th>
          </tr>
        </thead>

        <tbody>
          {displayed.map((p, i) => (
            <tr key={p.id} style={styles.row}>
              <td style={styles.td_pos}>#{i + 1}</td>
              <td style={styles.td_name}>{p.name}</td>
              <td style={styles.td_rating}>{getRatingByMode(p)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  container: {
    padding: 20,
    fontFamily: "Arial, sans-serif",
    maxWidth: 900,
    margin: "0 auto"
  },
  title: {
    textAlign: "center",
    marginBottom: 20
  },
  controls: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    marginBottom: 20
  },
  input: {
    padding: 10,
    border: "1px solid #ccc",
    borderRadius: 6,
    width: "100%",
    maxWidth: 300
  },
  buttons: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap"
  },
  btn: {
    padding: "8px 12px",
    border: "1px solid #ccc",
    background: "#f5f5f5",
    cursor: "pointer",
    borderRadius: 6
  },
  activeBtn: {
    padding: "8px 12px",
    border: "1px solid #000",
    background: "#000",
    color: "#fff",
    cursor: "pointer",
    borderRadius: 6
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    marginTop: 10
  },
  headRow: {
    background: "#eee"
  },
  row: {
    borderBottom: "1px solid #ddd"
  },
  th: {
    textAlign: "left",
    padding: "12px 10px"
  },
  th_name: {
    textAlign: "left",
    padding: "12px 10px",
    paddingLeft: 15
  },
  th_rating: {
    textAlign: "right",
    padding: "12px 15px"
  },
  td_pos: {
    padding: "12px 10px",
    fontWeight: "bold",
    color: "#666",
    width: "50px"
  },
  td_name: {
    padding: "12px 10px",
    paddingLeft: 15,
    textAlign: "left"
  },
  td_rating: {
    padding: "12px 15px",
    textAlign: "right",
    fontWeight: "bold"
  }
};