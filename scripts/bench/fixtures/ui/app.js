const todos = JSON.parse(localStorage.getItem("todos") || "[]");
const list = document.getElementById("todos");
for (const t of todos) {
  const li = document.createElement("li");
  li.textContent = t;
  list.appendChild(li);
}
