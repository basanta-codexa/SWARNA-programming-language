let rows = read_csv("examples/scores.csv", { name: String, team: String, score: Float })

let totals = {}
let counts = {}
let averages = {}

for row in rows {
    let team = row["team"]
    totals[team] = get(totals, team, 0.0) + row["score"]
    counts[team] = get(counts, team, 0) + 1
    averages[team] = totals[team] / counts[team]
}

print(averages)
