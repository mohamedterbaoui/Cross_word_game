const playBtn = document.querySelector("#play");
const wordDescription = document.querySelector("#word-description");
const username = document.querySelector(".profile h3");
const totalScore = document.querySelector("#total-score");
const points = document.querySelector("#points");
const timeText = document.querySelector(".remaining-time div:nth-child(2)");

let isGameActive = false;
let timer;
let timeLeft = GAME_CONFIG.time;
let revealInterval;
let pointPerReveal;
let revealedLetters = new Set();
let wordToGuess = "";
let pointsDeducted = false;

const hostURL = "https://cross-word-game.onrender.com/";

playBtn.addEventListener("click", startGame);

async function getRandomWord(language) {
  // Getting the number of total words in the DB
  // const totalWordsResponse = await fetch(hostURL + "word/count");
  const totalWords = 7100;

  let randomWord = null;

  // Loop to ensure the selected word matches the language
  while (!randomWord || randomWord.Lg !== language.toLowerCase()) {
    const randomIndex = Math.floor(Math.random() * totalWords.word_count) + 1;

    console.log(randomIndex);

    const response = await fetch(hostURL + `word/1/${randomIndex}`);
    const data = await response.json();

    randomWord = data.words[0];
    console.log(randomWord.Lg);
  }

  return randomWord;
}

async function getPlayerStats(username) {
  const response = await fetch(hostURL + `gamers/${username}`);
  const data = await response.json();
  return data;
}

async function startGame() {
  if (!isGameActive) {
    isGameActive = true;

    const inputUsername = document.querySelector("#username").value;

    if (!inputUsername) {
      alert("Please enter a username to start the game");
      isGameActive = false;
      return;
    }

    const playerStats = await getPlayerStats(inputUsername);
    if (playerStats.username) {
      username.textContent = playerStats.username;
      totalScore.textContent = playerStats.score;
    } else {
      alert("User does not exist");
      isGameActive = false;
      return;
    }

    // Clear previous letter boxes if any
    const oldBoxes = document.querySelector(".letter-boxes");
    if (oldBoxes) oldBoxes.remove();

    const wordData = await getRandomWord(GAME_CONFIG.lang);
    wordToGuess = wordData.Word.toUpperCase();

    hideHints();

    timeLeft = GAME_CONFIG.time;
    updateTimer();
    timer = setInterval(updateTimer, 1000);

    setTimeout(() => {
      const hintIcon = document.querySelector("#hint-icon");
      hintIcon.style.display = "block";
      hintIcon.style.visibility = "visible";
      pointsDeducted = false;

      hintIcon.addEventListener("click", () => {
        const suggestionsBox = document.querySelector(".suggestions-box");
        const suggestions = document.querySelector(".suggestions");
        suggestionsBox.style.visibility = "visible";
        suggestions.style.visibility = "visible";
        hintIcon.style.display = "none";

        if (!pointsDeducted) {
          deductPoints(20);
          pointsDeducted = true;
        }
      });
    }, 10000);

    wordDescription.textContent = wordData.definitions[0];
    points.textContent = wordToGuess.length * 10;
    createLetterBoxes(wordToGuess);

    const maxPoints = wordToGuess.length * 10;

    updateScoreBar(maxPoints, maxPoints);

    // Start interval to reveal letters every 10 seconds
    revealInterval = setInterval(() => {
      const inputs = document.querySelectorAll(".letter-box");
      const unrevealedIndices = [];

      inputs.forEach((input, index) => {
        if (!input.disabled && !input.value) {
          unrevealedIndices.push(index);
        }
      });

      if (unrevealedIndices.length === 0) {
        clearInterval(revealInterval);
        return;
      }

      const randomIndex =
        unrevealedIndices[Math.floor(Math.random() * unrevealedIndices.length)];
      const randomLetter = wordToGuess[randomIndex];
      showLetter(randomIndex, randomLetter);

      // Deduct 10 points
      deductPoints(10);
    }, GAME_CONFIG.hintInterval * 1000);

    console.log(wordData);
  }
}

async function handlePlayerInput(input) {
  // Normalize input to match case with wordToGuess
  input = input.toUpperCase();
  let correct = false;
  let allLettersRevealed = true;

  // First check if the full word matches
  if (input === wordToGuess) {
    // Reveal all letters
    for (let i = 0; i < wordToGuess.length; i++) {
      const box = document.querySelector(`#letter-box-${i}`);
      box.value = wordToGuess[i];
      box.disabled = true;
      box.classList.add("revealed");
    }

    // End the game with success
    clearInterval(timer);
    clearInterval(revealInterval);
    isGameActive = false;

    // Update player score with final calculation
    await updatePlayerScore(username.textContent);

    alert("Congratulations! You guessed the word correctly!");
    return;
  }

  // If not the full correct word, check for correct letters
  for (let i = 0; i < wordToGuess.length; i++) {
    const box = document.querySelector(`#letter-box-${i}`);

    // Skip boxes that are already revealed
    if (box.classList.contains("revealed")) {
      continue;
    }

    // If player entered something in this position
    if (input[i]) {
      if (input[i] === wordToGuess[i]) {
        // Correct letter in correct position
        box.value = wordToGuess[i];
        box.disabled = true;
        box.classList.add("revealed");
        correct = true;
      } else {
        // Incorrect letter, clear it
        box.value = "";
        allLettersRevealed = false;
      }
    } else {
      // No input for this position
      allLettersRevealed = false;
    }
  }

  // If not all letters are correct, deduct points
  if (!correct) {
    deductPoints(5);
  }

  // Check if all letters have been revealed through this process
  if (allLettersRevealed) {
    clearInterval(timer);
    clearInterval(revealInterval);
    isGameActive = false;

    // Update player score with final calculation
    await updatePlayerScore(username.textContent);

    alert("Congratulations! You guessed all the letters correctly!");
  }

  // Build updated pattern for suggestions
  let pattern = "";
  for (let i = 0; i < wordToGuess.length; i++) {
    const box = document.querySelector(`#letter-box-${i}`);
    pattern += box.value ? box.value : "_";
  }

  updateSuggestion(pattern);
}

function deductPoints(pointsToDeduct) {
  const currentPoints = parseInt(points.textContent);
  const newPoints = Math.max(currentPoints - pointsToDeduct, 0);
  points.textContent = newPoints;

  updateScoreBar(newPoints, wordToGuess.length * 10);
}

function hideHints() {
  const hintIcon = document.querySelector("#hint-icon");
  hintIcon.style.visibility = "hidden";

  const suggestionsBox = document.querySelector(".suggestions-box");
  const suggestions = document.querySelector(".suggestions");
  suggestionsBox.style.visibility = "hidden";
  suggestions.style.visibility = "hidden";
}

function updateTimer() {
  timeText.textContent = `${timeLeft}`;

  if (timeLeft <= 0) {
    clearInterval(timer);
    isGameActive = false;
    alert("Time's up!");
  }

  timeLeft--;
}

function showLetter(index, letter) {
  const input = document.querySelector(`#letter-box-${index}`);
  input.value = letter;
  input.disabled = true;
  input.classList.add("revealed", "auto-reveal");
  updateSuggestion();
}

async function updateSuggestion() {
  const inputs = document.querySelectorAll(".letter-box");
  let pattern = "";

  inputs.forEach((input) => {
    // Only use values from boxes that have been confirmed correct
    if (input.classList.contains("revealed")) {
      pattern += input.value.toLowerCase();
    } else {
      pattern += "_"; // Use underscore for unknown positions
    }
  });

  const response = await fetch(hostURL + `word/suggestions/${pattern}`);
  const data = await response.json();

  const suggestionBox = document.querySelector(".suggestions");
  suggestionBox.innerHTML = "";

  if (data.words.length === 0) {
    suggestionBox.innerHTML = "<p>No suggestions</p>";
  } else {
    data.words.forEach((word) => {
      const wordElem = document.createElement("div");
      wordElem.textContent = word;
      wordElem.classList.add("suggestion-word");

      // Add click event to handle selection
      wordElem.addEventListener("click", () => {
        handleSuggestionClick(word);
      });

      suggestionBox.appendChild(wordElem);
    });
  }
}

function handleSuggestionClick(selectedWord) {
  // Make sure game is active
  if (!isGameActive) return;

  // Convert to uppercase to match wordToGuess
  selectedWord = selectedWord.toUpperCase();

  if (selectedWord === wordToGuess) {
    // Correct word! Player wins
    for (let i = 0; i < wordToGuess.length; i++) {
      const box = document.querySelector(`#letter-box-${i}`);
      box.value = wordToGuess[i];
      box.disabled = true;
      box.classList.add("revealed");
    }

    // End the game with success
    clearInterval(timer);
    clearInterval(revealInterval);
    isGameActive = false;

    // Update player score with final calculation
    updatePlayerScore(username.textContent);
  } else {
    // Wrong word! Deduct points
    deductPoints(5);

    // Remove any existing feedback messages
    const existingFeedback = document.querySelector(".feedback-message");
    if (existingFeedback) {
      existingFeedback.remove();
    }

    // Display feedback to the player
    const feedbackElem = document.createElement("div");
    feedbackElem.textContent = "Incorrect word! -5 points";
    feedbackElem.classList.add("feedback-message", "incorrect");
    document.querySelector("#game-container").appendChild(feedbackElem);

    // Remove feedback message after 2 seconds
    setTimeout(() => {
      feedbackElem.remove();
    }, 2000);
  }
}

function calculateFinalScore() {
  const currentPoints = parseInt(points.textContent);

  // Compter uniquement les lettres révélées par le joueur (sans la classe auto-reveal)
  const inputs = document.querySelectorAll(".letter-box");
  let revealedByPlayer = 0;

  inputs.forEach((input) => {
    if (
      input.classList.contains("revealed") &&
      !input.classList.contains("auto-reveal")
    ) {
      revealedByPlayer++;
    }
  });

  const letterBonus = revealedByPlayer * 5;
  const timeBonus = Math.floor(timeLeft / 10);
  const finalScore = currentPoints + letterBonus + timeBonus;

  const scoreBreakdown = `
    Points restants: ${currentPoints}
    Lettres trouvées manuellement: ${revealedByPlayer} x 5 = ${letterBonus}
    Bonus temps (⌊${timeLeft}/10⌋): ${timeBonus}
    Score final: ${finalScore}
  `;

  alert(scoreBreakdown);
  return finalScore;
}

async function updatePlayerScore(playerUsername) {
  try {
    // Calculate final score with time bonus
    const finalScore = calculateFinalScore();

    // Send the updated score to the server
    const response = await fetch(hostURL + `gamers/update_score`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: playerUsername,
        score: finalScore,
      }),
    });

    const data = await response.json();
    console.log("Score updated:", data);

    // Update the total score display
    totalScore.textContent = data.total_score;
  } catch (error) {
    console.error("Error updating score:", error);
  }
}

function createLetterBoxes(word) {
  const inputContainer = document.createElement("div");
  inputContainer.className = "letter-boxes";

  // Create a box for each letter in the word
  for (let i = 0; i < word.length; i++) {
    const letterBox = document.createElement("input");
    letterBox.type = "text";
    letterBox.className = "letter-box";
    letterBox.maxLength = 1;
    letterBox.id = `letter-box-${i}`;
    letterBox.dataset.index = i;

    // Add event listeners to handle input and navigation
    letterBox.addEventListener("input", function (e) {
      // Move to next box if a letter was entered
      if (e.target.value && i < word.length - 1) {
        document.querySelector(`.letter-box[data-index="${i + 1}"]`).focus();
      }
    });

    // Handle backspace key
    letterBox.addEventListener("keydown", function (e) {
      if (e.key === "Backspace" && !e.target.value && i > 0) {
        // Move to previous box on backspace if current box is empty
        document.querySelector(`.letter-box[data-index="${i - 1}"]`).focus();
      }
    });

    inputContainer.appendChild(letterBox);
  }

  document.querySelector("#answer").appendChild(inputContainer);

  // Focus on first letter box
  inputContainer.querySelector(".letter-box").focus();

  // Listen for Enter key on the container
  inputContainer.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      const input = Array.from(inputContainer.querySelectorAll(".letter-box"))
        .map((box) => box.value.toLowerCase())
        .join("");

      handlePlayerInput(input); // Call the function to handle the input
    }
  });
}

function updateScoreBar(currentPoints, maxPoints) {
  const fill = document.querySelector("#score-fill");
  const percentage = Math.max((currentPoints / maxPoints) * 100, 0);
  fill.style.width = `${percentage}%`;
}
