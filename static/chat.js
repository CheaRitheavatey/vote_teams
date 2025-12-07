document.getElementById("send").addEventListener("click", send);

// Allow Enter key to send message
document.getElementById("msg").addEventListener("keypress", function(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    send();
  }
});

function send(){
  const user = document.getElementById("user").value || "User";
  const text = document.getElementById("msg").value;
  if(!text) return;
  fetch("/api/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({user, text})
  })
  .then(r => r.json())
  .then(data => {
    const box = document.getElementById("messages");
    // data.messages is an array
    data.messages.forEach(m=>{
      const el = document.createElement("div");
      el.className = m.from === user ? "msg user" : "msg bot";
      if (m.from === "VoteBot") {
        el.innerHTML =  `<strong>${m.from}:</strong> ${m.text}`;
      } else {
        el.textContent = `${m.from}: ${m.text}`;
      }
      box.appendChild(el);
    });
    document.getElementById("msg").value = "";
    box.scrollTop = box.scrollHeight;
  })
  .catch(e=>console.error(e));
}


const bubble = document.createElement("div");
bubble.className = "msg " + (m.from === "VoteBot" ? "bot" : "user");
bubble.innerHTML = m.text; // text already has <br> for results

row.appendChild(bubble);
container.appendChild(row);
