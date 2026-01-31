"""Cooperation system - creates challenges that require cooperation."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import random


class ChallengeType(Enum):
    """Types of cooperative challenges."""
    TWO_KEY = "two_key"          # Requires two agents to activate
    RESOURCE_POOLING = "resource_pooling"  # Requires combined resources
    DEFENSE = "defense"          # Defending against threat together
    CONSTRUCTION = "construction"  # Building requires multiple agents
    TRADE_ROUTE = "trade_route"   # Establishing trade requires trust


class ChallengeState(Enum):
    """State of a cooperative challenge."""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class CooperativeChallenge:
    """A challenge that requires cooperation to complete."""
    id: str
    challenge_type: ChallengeType
    name: str
    description: str

    # Requirements
    min_participants: int = 2
    max_participants: int = 4
    required_resources: dict[str, int] = field(default_factory=dict)
    required_actions: list[str] = field(default_factory=list)

    # State
    state: ChallengeState = ChallengeState.AVAILABLE
    current_participants: list[str] = field(default_factory=list)
    contributed_resources: dict[str, dict[str, int]] = field(default_factory=dict)
    completed_actions: dict[str, list[str]] = field(default_factory=dict)

    # Timing
    created_day: int = 1
    deadline_day: Optional[int] = None  # None = no deadline
    completed_day: Optional[int] = None

    # Rewards
    reward_resources: dict[str, int] = field(default_factory=dict)
    reward_reputation: float = 5.0
    reward_description: str = ""

    # Location
    location: Optional[str] = None


@dataclass
class Contract:
    """A formal agreement between agents."""
    id: str
    name: str
    parties: list[str]
    terms: str
    created_day: int

    # Obligations
    obligations: dict[str, list[str]] = field(default_factory=dict)  # agent -> obligations
    fulfilled: dict[str, list[str]] = field(default_factory=dict)  # agent -> fulfilled obligations

    # State
    is_active: bool = True
    is_violated: bool = False
    violated_by: Optional[str] = None
    violation_description: str = ""

    # Expiration
    expires_day: Optional[int] = None


class CooperationSystem:
    """
    Creates and manages challenges that require cooperation.

    Key mechanisms:
    - Two-key challenges (need two agents to unlock)
    - Resource pooling (combine resources for greater outcome)
    - Defensive cooperation (survive threats together)
    - Contract enforcement (trust through formal agreements)
    """

    def __init__(self):
        self.challenges: dict[str, CooperativeChallenge] = {}
        self.contracts: dict[str, Contract] = {}
        self._challenge_counter = 0
        self._contract_counter = 0

    def create_two_key_challenge(self, name: str, description: str,
                                location: str, reward: dict[str, int],
                                deadline_days: Optional[int] = None,
                                current_day: int = 1) -> CooperativeChallenge:
        """Create a challenge requiring two agents to activate simultaneously."""
        self._challenge_counter += 1
        challenge_id = f"challenge_{self._challenge_counter}"

        challenge = CooperativeChallenge(
            id=challenge_id,
            challenge_type=ChallengeType.TWO_KEY,
            name=name,
            description=description,
            min_participants=2,
            max_participants=2,
            required_actions=["activate_key_1", "activate_key_2"],
            reward_resources=reward,
            reward_description=f"Unlocks: {', '.join(f'{v} {k}' for k, v in reward.items())}",
            location=location,
            created_day=current_day,
            deadline_day=current_day + deadline_days if deadline_days else None,
        )

        self.challenges[challenge_id] = challenge
        return challenge

    def create_resource_pooling_challenge(self, name: str, description: str,
                                         required_resources: dict[str, int],
                                         reward: dict[str, int],
                                         min_participants: int = 2,
                                         current_day: int = 1) -> CooperativeChallenge:
        """Create a challenge requiring pooled resources."""
        self._challenge_counter += 1
        challenge_id = f"challenge_{self._challenge_counter}"

        challenge = CooperativeChallenge(
            id=challenge_id,
            challenge_type=ChallengeType.RESOURCE_POOLING,
            name=name,
            description=description,
            min_participants=min_participants,
            required_resources=required_resources,
            reward_resources=reward,
            reward_description=f"Pool {required_resources} for {reward}",
            created_day=current_day,
        )

        self.challenges[challenge_id] = challenge
        return challenge

    def create_defense_challenge(self, name: str, threat_description: str,
                                location: str, threat_level: int,
                                deadline_day: int,
                                current_day: int = 1) -> CooperativeChallenge:
        """Create a defensive challenge against a threat."""
        self._challenge_counter += 1
        challenge_id = f"challenge_{self._challenge_counter}"

        # Participants needed based on threat level
        min_participants = max(2, threat_level // 3)

        challenge = CooperativeChallenge(
            id=challenge_id,
            challenge_type=ChallengeType.DEFENSE,
            name=name,
            description=threat_description,
            min_participants=min_participants,
            required_actions=["defend"] * threat_level,
            reward_reputation=threat_level * 2,
            reward_description="Survive the threat together",
            location=location,
            created_day=current_day,
            deadline_day=deadline_day,
        )

        self.challenges[challenge_id] = challenge
        return challenge

    def join_challenge(self, challenge_id: str, agent_id: str) -> bool:
        """Have an agent join a challenge."""
        if challenge_id not in self.challenges:
            return False

        challenge = self.challenges[challenge_id]

        if challenge.state != ChallengeState.AVAILABLE:
            return False

        if agent_id in challenge.current_participants:
            return True  # Already joined

        if len(challenge.current_participants) >= challenge.max_participants:
            return False

        challenge.current_participants.append(agent_id)
        challenge.contributed_resources[agent_id] = {}
        challenge.completed_actions[agent_id] = []

        if len(challenge.current_participants) >= challenge.min_participants:
            challenge.state = ChallengeState.IN_PROGRESS

        return True

    def contribute_resource(self, challenge_id: str, agent_id: str,
                           resource: str, amount: int) -> bool:
        """Contribute resources to a challenge."""
        if challenge_id not in self.challenges:
            return False

        challenge = self.challenges[challenge_id]

        if agent_id not in challenge.current_participants:
            return False

        if challenge.state not in [ChallengeState.AVAILABLE, ChallengeState.IN_PROGRESS]:
            return False

        # Add contribution
        if resource not in challenge.contributed_resources[agent_id]:
            challenge.contributed_resources[agent_id][resource] = 0
        challenge.contributed_resources[agent_id][resource] += amount

        # Check if challenge is now completable
        self._check_challenge_completion(challenge)

        return True

    def perform_action(self, challenge_id: str, agent_id: str,
                      action: str) -> bool:
        """Perform a required action for a challenge."""
        if challenge_id not in self.challenges:
            return False

        challenge = self.challenges[challenge_id]

        if agent_id not in challenge.current_participants:
            return False

        if action not in challenge.required_actions:
            return False

        if action in challenge.completed_actions.get(agent_id, []):
            return True  # Already done

        challenge.completed_actions[agent_id].append(action)

        # Check completion
        self._check_challenge_completion(challenge)

        return True

    def _check_challenge_completion(self, challenge: CooperativeChallenge) -> bool:
        """Check if a challenge is now complete."""
        if challenge.state == ChallengeState.COMPLETED:
            return True

        # Check resource requirements
        if challenge.required_resources:
            total_contributed = {}
            for agent_contrib in challenge.contributed_resources.values():
                for resource, amount in agent_contrib.items():
                    total_contributed[resource] = total_contributed.get(resource, 0) + amount

            for resource, required in challenge.required_resources.items():
                if total_contributed.get(resource, 0) < required:
                    return False

        # Check action requirements
        if challenge.required_actions:
            all_actions = []
            for agent_actions in challenge.completed_actions.values():
                all_actions.extend(agent_actions)

            for action in challenge.required_actions:
                if action not in all_actions:
                    return False

        # All requirements met
        challenge.state = ChallengeState.COMPLETED
        return True

    def create_contract(self, name: str, parties: list[str],
                       terms: str, obligations: dict[str, list[str]],
                       current_day: int,
                       duration_days: Optional[int] = None) -> Contract:
        """Create a formal contract between agents."""
        self._contract_counter += 1
        contract_id = f"contract_{self._contract_counter}"

        contract = Contract(
            id=contract_id,
            name=name,
            parties=parties,
            terms=terms,
            created_day=current_day,
            obligations=obligations,
            fulfilled={agent: [] for agent in parties},
            expires_day=current_day + duration_days if duration_days else None,
        )

        self.contracts[contract_id] = contract
        return contract

    def fulfill_obligation(self, contract_id: str, agent_id: str,
                          obligation: str) -> bool:
        """Mark an obligation as fulfilled."""
        if contract_id not in self.contracts:
            return False

        contract = self.contracts[contract_id]

        if agent_id not in contract.parties:
            return False

        if not contract.is_active:
            return False

        if obligation not in contract.obligations.get(agent_id, []):
            return False

        if obligation not in contract.fulfilled[agent_id]:
            contract.fulfilled[agent_id].append(obligation)

        return True

    def violate_contract(self, contract_id: str, violator: str,
                        description: str) -> bool:
        """Record a contract violation."""
        if contract_id not in self.contracts:
            return False

        contract = self.contracts[contract_id]

        if violator not in contract.parties:
            return False

        contract.is_violated = True
        contract.violated_by = violator
        contract.violation_description = description

        return True

    def process_day(self, current_day: int) -> dict:
        """Process daily updates for challenges and contracts."""
        results = {
            "expired_challenges": [],
            "completed_challenges": [],
            "expired_contracts": [],
        }

        # Check challenge deadlines
        for challenge in self.challenges.values():
            if challenge.state == ChallengeState.IN_PROGRESS:
                if challenge.deadline_day and current_day > challenge.deadline_day:
                    challenge.state = ChallengeState.FAILED
                    results["expired_challenges"].append(challenge.id)
            elif challenge.state == ChallengeState.COMPLETED:
                results["completed_challenges"].append(challenge.id)

        # Check contract expirations
        for contract in self.contracts.values():
            if contract.is_active and contract.expires_day:
                if current_day > contract.expires_day:
                    contract.is_active = False
                    results["expired_contracts"].append(contract.id)

        return results

    def get_available_challenges(self, agent_id: Optional[str] = None) -> list[CooperativeChallenge]:
        """Get all available challenges, optionally filtered by participant eligibility."""
        available = []
        for challenge in self.challenges.values():
            if challenge.state == ChallengeState.AVAILABLE:
                if agent_id is None or agent_id not in challenge.current_participants:
                    available.append(challenge)
            elif challenge.state == ChallengeState.IN_PROGRESS:
                if agent_id and agent_id in challenge.current_participants:
                    available.append(challenge)
        return available

    def get_agent_contracts(self, agent_id: str) -> list[Contract]:
        """Get all contracts involving an agent."""
        return [c for c in self.contracts.values() if agent_id in c.parties]

    def get_challenge_progress(self, challenge_id: str) -> Optional[dict]:
        """Get progress report for a challenge."""
        if challenge_id not in self.challenges:
            return None

        challenge = self.challenges[challenge_id]

        # Calculate resource progress
        resource_progress = {}
        if challenge.required_resources:
            total = {}
            for contrib in challenge.contributed_resources.values():
                for r, a in contrib.items():
                    total[r] = total.get(r, 0) + a

            for resource, required in challenge.required_resources.items():
                current = total.get(resource, 0)
                resource_progress[resource] = {
                    "current": current,
                    "required": required,
                    "percentage": min(100, int(current / required * 100)),
                }

        # Calculate action progress
        action_progress = {}
        if challenge.required_actions:
            all_actions = []
            for actions in challenge.completed_actions.values():
                all_actions.extend(actions)

            for action in set(challenge.required_actions):
                required = challenge.required_actions.count(action)
                current = all_actions.count(action)
                action_progress[action] = {
                    "current": current,
                    "required": required,
                    "percentage": min(100, int(current / required * 100)),
                }

        return {
            "challenge_id": challenge_id,
            "state": challenge.state.value,
            "participants": challenge.current_participants,
            "resource_progress": resource_progress,
            "action_progress": action_progress,
        }

    def generate_random_challenge(self, current_day: int,
                                 location: Optional[str] = None) -> CooperativeChallenge:
        """Generate a random cooperative challenge."""
        challenge_templates = [
            {
                "type": "two_key",
                "name": "Ancient Vault",
                "description": "An ancient vault with two keyholes. Both keys must be turned simultaneously.",
                "reward": {"gold": 5, "diamond": 1},
            },
            {
                "type": "resource_pooling",
                "name": "Build a Bridge",
                "description": "A river blocks the path. Pool wood to build a bridge.",
                "required": {"wood": 20},
                "reward": {"reputation": 10},
            },
            {
                "type": "defense",
                "name": "Night Raid",
                "description": "A horde approaches. Stand together or fall alone.",
                "threat_level": 6,
            },
        ]

        template = random.choice(challenge_templates)

        if template["type"] == "two_key":
            return self.create_two_key_challenge(
                template["name"],
                template["description"],
                location or "unknown",
                template["reward"],
                deadline_days=5,
                current_day=current_day,
            )
        elif template["type"] == "resource_pooling":
            return self.create_resource_pooling_challenge(
                template["name"],
                template["description"],
                template["required"],
                template.get("reward", {}),
                current_day=current_day,
            )
        else:
            return self.create_defense_challenge(
                template["name"],
                template["description"],
                location or "unknown",
                template["threat_level"],
                current_day + 1,
                current_day,
            )
