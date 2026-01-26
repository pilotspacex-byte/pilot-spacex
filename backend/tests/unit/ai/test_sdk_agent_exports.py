"""Tests for SDK agent exports in __init__.py.

Verifies that:
1. All SDK base classes are exported
2. All SDK agents are exported with SDK suffix
3. All SDK model classes are exported with SDK prefix
4. Legacy agents remain available
5. No naming conflicts between SDK and legacy exports
"""

from __future__ import annotations

import pytest

from pilot_space.ai.agents import (
    # Legacy Base Classes
    AgentContext,
    AgentResult,
    # Legacy Agents
    AssigneeRecommenderAgent,
    # SDK Agents
    AssigneeRecommenderAgentSDK,
    BaseAgent,
    CommitLinkerAgent,
    CommitLinkerAgentSDK,
    ConversationAgent,
    ConversationAgentSDK,
    ConversationManager,
    ConversationManagerSDK,
    DuplicateDetectorAgent,
    DuplicateDetectorAgentSDK,
    IssueEnhancerAgent,
    IssueEnhancerAgentSDK,
    MarginAnnotationAgentSDK,
    # SDK Base Classes
    SDKAgentContext,
    SDKAgentResult,
    SDKBaseAgent,
    StreamingSDKBaseAgent,
)


class TestSDKBaseExports:
    """Test SDK base class exports."""

    def test_sdk_agent_context_exported(self) -> None:
        """Verify SDKAgentContext is exported."""
        assert SDKAgentContext is not None
        assert SDKAgentContext.__name__ == "AgentContext"

    def test_sdk_agent_result_exported(self) -> None:
        """Verify SDKAgentResult is exported."""
        assert SDKAgentResult is not None
        assert SDKAgentResult.__name__ == "AgentResult"

    def test_sdk_base_agent_exported(self) -> None:
        """Verify SDKBaseAgent is exported."""
        assert SDKBaseAgent is not None
        assert SDKBaseAgent.__name__ == "SDKBaseAgent"

    def test_streaming_sdk_base_agent_exported(self) -> None:
        """Verify StreamingSDKBaseAgent is exported."""
        assert StreamingSDKBaseAgent is not None
        assert StreamingSDKBaseAgent.__name__ == "StreamingSDKBaseAgent"


class TestSDKAgentExports:
    """Test SDK agent exports."""

    @pytest.mark.parametrize(
        ("agent_class", "expected_base"),
        [
            (AssigneeRecommenderAgentSDK, SDKBaseAgent),
            (CommitLinkerAgentSDK, SDKBaseAgent),
            (ConversationAgentSDK, StreamingSDKBaseAgent),
            (DuplicateDetectorAgentSDK, SDKBaseAgent),
            (IssueEnhancerAgentSDK, SDKBaseAgent),
            (MarginAnnotationAgentSDK, SDKBaseAgent),
        ],
    )
    def test_sdk_agent_inheritance(
        self, agent_class: type, expected_base: type
    ) -> None:
        """Verify SDK agents inherit from correct base class."""
        assert issubclass(agent_class, expected_base)

    @pytest.mark.parametrize(
        ("agent_class", "expected_agent_name"),
        [
            (AssigneeRecommenderAgentSDK, "assignee_recommender"),
            (CommitLinkerAgentSDK, "commit_linker"),
            (ConversationAgentSDK, "conversation"),
            (DuplicateDetectorAgentSDK, "duplicate_detector"),
            (IssueEnhancerAgentSDK, "issue_enhancer"),
            (MarginAnnotationAgentSDK, "margin_annotation"),
        ],
    )
    def test_sdk_agent_name_attribute(
        self, agent_class: type, expected_agent_name: str
    ) -> None:
        """Verify SDK agents have correct AGENT_NAME attribute."""
        assert hasattr(agent_class, "AGENT_NAME")
        assert expected_agent_name == agent_class.AGENT_NAME

    @pytest.mark.parametrize(
        "agent_class",
        [
            AssigneeRecommenderAgentSDK,
            CommitLinkerAgentSDK,
            ConversationAgentSDK,
            DuplicateDetectorAgentSDK,
            IssueEnhancerAgentSDK,
            MarginAnnotationAgentSDK,
        ],
    )
    def test_sdk_agent_default_model_attribute(self, agent_class: type) -> None:
        """Verify SDK agents have DEFAULT_MODEL attribute."""
        assert hasattr(agent_class, "DEFAULT_MODEL")
        assert isinstance(agent_class.DEFAULT_MODEL, str)
        assert len(agent_class.DEFAULT_MODEL) > 0


class TestLegacyAgentExports:
    """Test legacy agent exports remain available."""

    @pytest.mark.parametrize(
        ("legacy_class", "sdk_class"),
        [
            (AssigneeRecommenderAgent, AssigneeRecommenderAgentSDK),
            (CommitLinkerAgent, CommitLinkerAgentSDK),
            (ConversationAgent, ConversationAgentSDK),
            (DuplicateDetectorAgent, DuplicateDetectorAgentSDK),
            (IssueEnhancerAgent, IssueEnhancerAgentSDK),
        ],
    )
    def test_legacy_agent_available(
        self, legacy_class: type, sdk_class: type
    ) -> None:
        """Verify legacy agents are still exported."""
        assert legacy_class is not None
        # Verify they're different classes
        assert legacy_class is not sdk_class

    def test_legacy_base_classes_available(self) -> None:
        """Verify legacy base classes are still exported."""
        assert AgentContext is not None
        assert AgentResult is not None
        assert BaseAgent is not None

    def test_legacy_conversation_manager_available(self) -> None:
        """Verify legacy ConversationManager is still exported."""
        assert ConversationManager is not None
        assert ConversationManagerSDK is not None
        # Verify they're different classes
        assert ConversationManager is not ConversationManagerSDK


class TestNoNamingConflicts:
    """Test that there are no naming conflicts between SDK and legacy exports."""

    def test_sdk_agent_context_vs_legacy_agent_context(self) -> None:
        """Verify SDK and legacy AgentContext are distinct."""
        # They have the same name but different imports
        assert SDKAgentContext.__module__ == "pilot_space.ai.agents.sdk_base"
        assert AgentContext.__module__ == "pilot_space.ai.agents.base"

    def test_sdk_agent_result_vs_legacy_agent_result(self) -> None:
        """Verify SDK and legacy AgentResult are distinct."""
        # They have the same name but different imports
        assert SDKAgentResult.__module__ == "pilot_space.ai.agents.sdk_base"
        assert AgentResult.__module__ == "pilot_space.ai.agents.base"

    def test_agent_class_names_are_unique(self) -> None:
        """Verify all agent class names are unique."""
        agent_classes = [
            AssigneeRecommenderAgent,
            AssigneeRecommenderAgentSDK,
            CommitLinkerAgent,
            CommitLinkerAgentSDK,
            ConversationAgent,
            ConversationAgentSDK,
            DuplicateDetectorAgent,
            DuplicateDetectorAgentSDK,
            IssueEnhancerAgent,
            IssueEnhancerAgentSDK,
        ]

        # Create set of class objects (not names)
        class_set = set(agent_classes)

        # All classes should be unique objects
        assert len(class_set) == len(agent_classes)


class TestSDKAgentMethods:
    """Test that SDK agents have required methods."""

    @pytest.mark.parametrize(
        "agent_class",
        [
            AssigneeRecommenderAgentSDK,
            CommitLinkerAgentSDK,
            ConversationAgentSDK,
            DuplicateDetectorAgentSDK,
            IssueEnhancerAgentSDK,
            MarginAnnotationAgentSDK,
        ],
    )
    def test_sdk_agent_has_execute_method(self, agent_class: type) -> None:
        """Verify SDK agents have execute method."""
        assert hasattr(agent_class, "execute")
        assert callable(agent_class.execute)

    @pytest.mark.parametrize(
        "agent_class",
        [
            AssigneeRecommenderAgentSDK,
            CommitLinkerAgentSDK,
            ConversationAgentSDK,
            DuplicateDetectorAgentSDK,
            IssueEnhancerAgentSDK,
            MarginAnnotationAgentSDK,
        ],
    )
    def test_sdk_agent_has_run_method(self, agent_class: type) -> None:
        """Verify SDK agents have run method (from base class)."""
        assert hasattr(agent_class, "run")
        assert callable(agent_class.run)

    def test_streaming_sdk_agent_has_stream_method(self) -> None:
        """Verify streaming SDK agent has stream method."""
        assert hasattr(ConversationAgentSDK, "stream")
        assert callable(ConversationAgentSDK.stream)
