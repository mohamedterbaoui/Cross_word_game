document.addEventListener("DOMContentLoaded", () => {
  const wordDisplay = document.getElementById("word-display");
  const form = document.getElementById("definition-form");
  const definitionInput = document.getElementById("definition-input");
  const playerNameInput = document.getElementById("player-name");
  const messages = document.getElementById("messages");

  let currentWord = "";
  let submittedDefinitions = new Set();

  let timeLeft = CONFIG.time;

  async function getRandomWord(language) {
    // Getting the number of total words in the DB
    const totalWordsResponse = await fetch("http://localhost:5000/word/count");
    const totalWords = await totalWordsResponse.json();

    let randomWord = null;

    // Loop to ensure the selected word matches the language
    while (!randomWord || randomWord.Lg !== language.toLowerCase()) {
      const randomIndex = Math.floor(Math.random() * totalWords.word_count) + 1;

      const response = await fetch(
        `http://localhost:5000/word/1/${randomIndex}`
      );
      const data = await response.json();

      randomWord = data.words[0];
      console.log(randomWord);
    }

    return randomWord;
  }

  async function initGame() {
    const wordObj = await getRandomWord(CONFIG.lang);
    currentWord = wordObj.Word;
    wordDisplay.textContent = currentWord;
  }

  initGame();

  // 2. Timer countdown
  const countdown = setInterval(() => {
    timeLeft--;
    document.querySelector(
      "p:nth-child(2)"
    ).textContent = `Time: ${timeLeft} seconds`;
    if (timeLeft <= 0) {
      clearInterval(countdown);
      form.querySelector("button").disabled = true;
      messages.textContent = "⏱ Time's up!";
      messages.style.color = "red";
    }
  }, 1000);

  async function updatePlayerScore(playerName, scoreToAdd) {
    try {
      const response = await fetch(
        "http://localhost:5000/gamers/update_score",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username: playerName,
            score: scoreToAdd,
          }),
        }
      );

      const result = await response.json();
      if (response.ok) {
        console.log("Score updated:", result);
      } else {
        console.error("Failed to update score:", result.error);
      }
    } catch (err) {
      console.error("Error during score update:", err);
    }
  }

  // 3. Handle form submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const definition = definitionInput.value.trim();
    const playerName = playerNameInput.value.trim();

    // Validation
    if (definition.length < 5 || definition.length > 200) {
      messages.textContent = " Definition must be 5–200 characters.";
      messages.style.color = "red";
      return;
    }
    if (submittedDefinitions.has(definition.toLowerCase())) {
      messages.textContent = " You already submitted that!";
      messages.style.color = "red";
      return;
    }

    // 4. Send to backend
    const response = await fetch("/word/add_definition", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        word: currentWord,
        definition: definition,
        player: playerName,
      }),
    });
    const result = await response.json();
    if (response.ok) {
      submittedDefinitions.add(definition);
      messages.textContent =
        "✅ Definition submitted! You get +5 in your score";
      messages.style.color = "green";

      // ✅ Update score here
      await updatePlayerScore(playerName, 5);

      definitionInput.value = ""; // reset input
    } else {
      messages.textContent = `❌ Error: ${
        result.error || "Submission failed."
      }`;
      messages.style.color = "red";
    }
  });
});
