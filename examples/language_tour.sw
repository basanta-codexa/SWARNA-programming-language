# A short tour of SWARNA: functions, lists, slicing, maps, strings, and errors.

fn grade_label(score: Int) -> String {
    if score >= 90 { "A" } else if score >= 80 { "B" } else { "C" }
}

fn total(scores: List[Int]) -> Int {
    let sum_value = 0
    for score in scores { sum_value = sum_value + score }
    sum_value
}

let students = ["Ada", "Grace", "Linus"]
let scores = [92, 85, 77]

print("Grade report")
print(upper(students[0]) + ": " + grade_label(scores[0]))

let results: Map[String, Int] = {}
for i in range(len(students)) {
    results[students[i]] = scores[i]
}

for name in students {
    print(name + " scored " + str(get(results, name, 0)))
}

print(scores[1:3])
print(total(scores))

try {
    throw "missing submission"
} catch error {
    print("Skipped: " + error)
}

print("Done")
