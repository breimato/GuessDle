(function (global) {
  function formatEloAmount(amount) {
    const value = Number(amount);
    if (Number.isNaN(value)) return "0";
    return Number.isInteger(value) ? String(value) : value.toFixed(1);
  }

  function buildModalTitle(outcome, displayName) {
    if (outcome === "surrender") {
      return `¡Qué lástima! El personaje era ${displayName}`;
    }
    return `¡Correcto! ${displayName}`;
  }

  function normalizeChallengeData(data) {
    if (!data) return null;
    const currentUser = data.current_user
      ?? (typeof CHALLENGE_CURRENT_USER !== "undefined" ? CHALLENGE_CURRENT_USER : "");
    return {
      completed: Boolean(data.completed),
      current_user: currentUser,
      challenger: data.challenger ?? data.challenger_username ?? "",
      opponent: data.opponent ?? data.opponent_username ?? "",
      winner: data.winner ?? data.winner_username ?? null,
      challenger_attempts: data.challenger_attempts,
      opponent_attempts: data.opponent_attempts,
      stake_points: Number(data.stake_points || 0),
      points_delta: data.points_delta != null ? Number(data.points_delta) : null,
    };
  }

  function challengeRoleContext(challenge) {
    const isChallenger = challenge.current_user === challenge.challenger;
    return {
      rivalUsername: isChallenger ? challenge.opponent : challenge.challenger,
      userAttempts: isChallenger ? challenge.challenger_attempts : challenge.opponent_attempts,
      rivalAttempts: isChallenger ? challenge.opponent_attempts : challenge.challenger_attempts,
    };
  }

  function resolveChallengeOutcome(challenge) {
    if (!challenge.completed) return "waiting";
    if (challenge.winner === challenge.current_user) return "win";
    if (challenge.winner) return "loss";
    return "tie";
  }

  const CHALLENGE_MESSAGE_BUILDERS = {
    waiting(challenge, role) {
      const attemptsLabel = role.userAttempts != null
        ? `${role.userAttempts} intentos`
        : "tus intentos";
      return `<p class="arcade-msg--wait">Partida completada (${attemptsLabel}). Esperando a tu rival…</p>`;
    },
    win(challenge, role) {
      const pointsWon = challenge.points_delta != null
        ? challenge.points_delta
        : challenge.stake_points;
      return `<p class="arcade-msg--win">¡Has ganado el reto contra ${role.rivalUsername}! (${role.userAttempts} vs ${role.rivalAttempts})<br>+${formatEloAmount(pointsWon)} ELO</p>`;
    },
    loss(challenge, role) {
      const pointsLost = challenge.points_delta != null
        ? Math.abs(challenge.points_delta)
        : challenge.stake_points;
      return `<p class="arcade-msg--loss">Has perdido el reto contra ${role.rivalUsername}. (${role.userAttempts} vs ${role.rivalAttempts})<br>-${formatEloAmount(pointsLost)} ELO</p>`;
    },
    tie(challenge, role) {
      const pointsLost = challenge.points_delta != null
        ? Math.abs(challenge.points_delta)
        : challenge.stake_points;
      return `<p class="arcade-msg--tie">Empate contra ${role.rivalUsername}. (${role.userAttempts} vs ${role.rivalAttempts})<br>-${formatEloAmount(pointsLost)} ELO</p>`;
    },
  };

  function buildChallengeMessageHtml(challengeData) {
    const challenge = normalizeChallengeData(challengeData);
    if (!challenge) return "";
    const outcome = resolveChallengeOutcome(challenge);
    const role = challengeRoleContext(challenge);
    return CHALLENGE_MESSAGE_BUILDERS[outcome](challenge, role);
  }

  function buildBetMessageHtml(betInfo) {
    if (!betInfo) return "";
    if (betInfo.betWon) {
      return `<p class="arcade-msg--bet-win">¡Apuesta ganada! +${formatEloAmount(betInfo.netProfit)} ELO</p>`;
    }
    return `<p class="arcade-msg--bet-loss">Apuesta perdida. Has perdido ${formatEloAmount(betInfo.betAmount)} ELO.</p>`;
  }

  function buildBetStatusMessage({ won, betInfo, betAmount, average, currentAttempts }) {
    if (won) {
      if (betInfo?.betWon) {
        return {
          text: `¡Apuesta ganada! +${formatEloAmount(betInfo.netProfit)} ELO`,
          className: "mt-2 font-bold text-center text-lg arcade-msg--bet-win",
          visible: true,
        };
      }
      return {
        text: `¡Apuesta perdida! Has perdido ${formatEloAmount(betAmount)} ELO.`,
        className: "mt-2 font-bold text-center text-lg arcade-msg--bet-loss",
        visible: true,
      };
    }
    if (average !== null && Number(currentAttempts) > average) {
      return {
        text: `¡Apuesta perdida! Has perdido ${formatEloAmount(betAmount)} ELO.`,
        className: "mt-2 font-bold text-center text-lg arcade-msg--bet-loss",
        visible: true,
      };
    }
    return { text: "", className: "", visible: false };
  }

  global.GuessDlePlayMessages = {
    formatEloAmount,
    buildModalTitle,
    normalizeChallengeData,
    buildChallengeMessageHtml,
    buildBetMessageHtml,
    buildBetStatusMessage,
  };
})(window);
