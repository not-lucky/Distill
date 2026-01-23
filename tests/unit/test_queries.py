"""Tests for src/queries.py - Database query utilities."""

from datetime import datetime, timedelta
import pytest
from unittest.mock import patch, MagicMock

from assertpy import assert_that

from src.database import Run, Problem, ProviderResult, Card, DatabaseManager
from src.queries import (
    get_runs,
    get_problems_by_run,
    get_problems_by_question,
    get_provider_results_by_problem,
    get_provider_results_by_run,
    get_cards_by_problem,
    get_cards_by_run,
    search_cards,
    get_run_statistics,
    compare_runs,
)


class TestGetRuns:
    """Tests for get_runs function."""

    def test_get_runs_no_filters(self, in_memory_db):
        """
        Given runs exist in database
        When get_runs is called with no filters
        Then it returns all runs
        """
        with in_memory_db.session_scope() as session:
            run1 = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            run2 = Run(id="run-2", mode="cs", subject="cs", card_type="standard", status="running")
            session.add_all([run1, run2])

        result = get_runs()

        assert_that(result).is_length(2)

    def test_get_runs_filter_by_mode(self, in_memory_db):
        """
        Given runs with different modes
        When get_runs is called with mode filter
        Then it returns only matching runs
        """
        with in_memory_db.session_scope() as session:
            run1 = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            run2 = Run(id="run-2", mode="cs", subject="cs", card_type="standard", status="completed")
            session.add_all([run1, run2])

        result = get_runs(mode="leetcode")

        assert_that(result).is_length(1)
        assert_that(result[0].mode).is_equal_to("leetcode")

    def test_get_runs_filter_by_subject(self, in_memory_db):
        """
        Given runs with different subjects
        When get_runs is called with subject filter
        Then it returns only matching runs
        """
        with in_memory_db.session_scope() as session:
            run1 = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            run2 = Run(id="run-2", mode="physics", subject="physics", card_type="standard", status="completed")
            session.add_all([run1, run2])

        result = get_runs(subject="physics")

        assert_that(result).is_length(1)
        assert_that(result[0].subject).is_equal_to("physics")

    def test_get_runs_filter_by_status(self, in_memory_db):
        """
        Given runs with different statuses
        When get_runs is called with status filter
        Then it returns only matching runs
        """
        with in_memory_db.session_scope() as session:
            run1 = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            run2 = Run(id="run-2", mode="cs", subject="cs", card_type="standard", status="running")
            session.add_all([run1, run2])

        result = get_runs(status="running")

        assert_that(result).is_length(1)
        assert_that(result[0].status).is_equal_to("running")

    def test_get_runs_filter_by_user_label(self, in_memory_db):
        """
        Given runs with user labels
        When get_runs is called with user_label filter (partial match)
        Then it returns matching runs
        """
        with in_memory_db.session_scope() as session:
            run1 = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed", user_label="test-batch-1")
            run2 = Run(id="run-2", mode="cs", subject="cs", card_type="standard", status="completed", user_label="production-run")
            session.add_all([run1, run2])

        result = get_runs(user_label="batch")

        assert_that(result).is_length(1)
        assert_that(result[0].user_label).contains("batch")

    def test_get_runs_empty_result(self, in_memory_db):
        """
        Given no runs in database
        When get_runs is called
        Then it returns empty list
        """
        result = get_runs()

        assert_that(result).is_empty()


class TestGetProblemsByRun:
    """Tests for get_problems_by_run function."""

    def test_get_problems_by_run_with_matches(self, in_memory_db):
        """
        Given problems exist for a run
        When get_problems_by_run is called
        Then it returns all problems for that run
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem1 = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            problem2 = Problem(run_id="run-1", question_name="Two Sum", sanitized_name="two_sum", status="success")
            session.add_all([run, problem1, problem2])

        result = get_problems_by_run("run-1")

        assert_that(result).is_length(2)

    def test_get_problems_by_run_no_matches(self, in_memory_db):
        """
        Given no problems for a run
        When get_problems_by_run is called
        Then it returns empty list
        """
        result = get_problems_by_run("nonexistent-run")

        assert_that(result).is_empty()


class TestGetProblemsByQuestion:
    """Tests for get_problems_by_question function."""

    def test_get_problems_by_question_partial_match(self, in_memory_db):
        """
        Given problems with various question names
        When get_problems_by_question is called with partial name
        Then it returns matching problems
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem1 = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            problem2 = Problem(run_id="run-1", question_name="Search a 2D Matrix", sanitized_name="search_2d_matrix", status="success")
            problem3 = Problem(run_id="run-1", question_name="Two Sum", sanitized_name="two_sum", status="success")
            session.add_all([run, problem1, problem2, problem3])

        result = get_problems_by_question("Search")

        assert_that(result).is_length(2)

    def test_get_problems_by_question_no_matches(self, in_memory_db):
        """
        Given problems in database
        When get_problems_by_question is called with non-matching name
        Then it returns empty list
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])

        result = get_problems_by_question("Nonexistent")

        assert_that(result).is_empty()


class TestGetProviderResultsByProblem:
    """Tests for get_provider_results_by_problem function."""

    def test_get_provider_results_by_problem_with_matches(self, in_memory_db):
        """
        Given provider results exist for a problem
        When get_provider_results_by_problem is called
        Then it returns all results for that problem
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            pr1 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="cerebras", provider_model="llama-3.1-70b", success=True)
            pr2 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="openrouter", provider_model="gpt-4", success=True)
            session.add_all([pr1, pr2])
            session.flush()
            problem_id = problem.id

        result = get_provider_results_by_problem(problem_id)

        assert_that(result).is_length(2)

    def test_get_provider_results_by_problem_no_matches(self, in_memory_db):
        """
        Given no provider results for a problem
        When get_provider_results_by_problem is called
        Then it returns empty list
        """
        result = get_provider_results_by_problem(99999)

        assert_that(result).is_empty()


class TestGetProviderResultsByRun:
    """Tests for get_provider_results_by_run function."""

    def test_get_provider_results_by_run_no_filters(self, in_memory_db):
        """
        Given provider results for a run
        When get_provider_results_by_run is called with no filters
        Then it returns all results
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            pr1 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="cerebras", provider_model="llama-3.1-70b", success=True)
            pr2 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="openrouter", provider_model="gpt-4", success=False)
            session.add_all([pr1, pr2])

        result = get_provider_results_by_run("run-1")

        assert_that(result).is_length(2)

    def test_get_provider_results_by_run_filter_by_provider(self, in_memory_db):
        """
        Given provider results from multiple providers
        When get_provider_results_by_run is called with provider filter
        Then it returns only matching results
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            pr1 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="cerebras", provider_model="llama-3.1-70b", success=True)
            pr2 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="openrouter", provider_model="gpt-4", success=True)
            session.add_all([pr1, pr2])

        result = get_provider_results_by_run("run-1", provider_name="cerebras")

        assert_that(result).is_length(1)
        assert_that(result[0].provider_name).is_equal_to("cerebras")

    def test_get_provider_results_by_run_filter_by_success(self, in_memory_db):
        """
        Given provider results with different success statuses
        When get_provider_results_by_run is called with success filter
        Then it returns only matching results
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            pr1 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="cerebras", provider_model="llama-3.1-70b", success=True)
            pr2 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="openrouter", provider_model="gpt-4", success=False)
            session.add_all([pr1, pr2])

        result = get_provider_results_by_run("run-1", success=False)

        assert_that(result).is_length(1)
        assert_that(result[0].success).is_false()


class TestGetCardsByProblem:
    """Tests for get_cards_by_problem function."""

    def test_get_cards_by_problem_with_matches(self, in_memory_db):
        """
        Given cards exist for a problem
        When get_cards_by_problem is called
        Then it returns cards ordered by card_index
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            card1 = Card(problem_id=problem.id, run_id="run-1", front="Q1", back="A1", card_index=1, card_type="Basic")
            card2 = Card(problem_id=problem.id, run_id="run-1", front="Q2", back="A2", card_index=0, card_type="Basic")
            session.add_all([card1, card2])
            session.flush()
            problem_id = problem.id

        result = get_cards_by_problem(problem_id)

        assert_that(result).is_length(2)
        assert_that(result[0].card_index).is_equal_to(0)
        assert_that(result[1].card_index).is_equal_to(1)

    def test_get_cards_by_problem_no_matches(self, in_memory_db):
        """
        Given no cards for a problem
        When get_cards_by_problem is called
        Then it returns empty list
        """
        result = get_cards_by_problem(99999)

        assert_that(result).is_empty()


class TestGetCardsByRun:
    """Tests for get_cards_by_run function."""

    def test_get_cards_by_run_no_filter(self, in_memory_db):
        """
        Given cards for a run
        When get_cards_by_run is called
        Then it returns all cards
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            card1 = Card(problem_id=problem.id, run_id="run-1", front="Q1", back="A1", card_index=0, card_type="Basic")
            card2 = Card(problem_id=problem.id, run_id="run-1", front="Q2", back="A2", card_index=1, card_type="Algorithm")
            session.add_all([card1, card2])

        result = get_cards_by_run("run-1")

        assert_that(result).is_length(2)

    def test_get_cards_by_run_filter_by_card_type(self, in_memory_db):
        """
        Given cards of different types
        When get_cards_by_run is called with card_type filter
        Then it returns only matching cards
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            card1 = Card(problem_id=problem.id, run_id="run-1", front="Q1", back="A1", card_index=0, card_type="Basic")
            card2 = Card(problem_id=problem.id, run_id="run-1", front="Q2", back="A2", card_index=1, card_type="Algorithm")
            session.add_all([card1, card2])

        result = get_cards_by_run("run-1", card_type="Algorithm")

        assert_that(result).is_length(1)
        assert_that(result[0].card_type).is_equal_to("Algorithm")

    def test_get_cards_by_run_empty_result(self, in_memory_db):
        """
        Given no cards for a run
        When get_cards_by_run is called
        Then it returns empty list
        """
        result = get_cards_by_run("nonexistent-run")

        assert_that(result).is_empty()


class TestSearchCards:
    """Tests for search_cards function."""

    def test_search_cards_matches_front(self, in_memory_db):
        """
        Given cards in database
        When search_cards is called with query matching front
        Then it returns matching cards
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            card1 = Card(problem_id=problem.id, run_id="run-1", front="What is binary search?", back="A1", card_index=0, card_type="Basic")
            card2 = Card(problem_id=problem.id, run_id="run-1", front="Other question", back="A2", card_index=1, card_type="Basic")
            session.add_all([card1, card2])

        result = search_cards("binary")

        assert_that(result).is_length(1)
        assert_that(result[0].front).contains("binary")

    def test_search_cards_matches_back(self, in_memory_db):
        """
        Given cards in database
        When search_cards is called with query matching back
        Then it returns matching cards
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            card1 = Card(problem_id=problem.id, run_id="run-1", front="Q1", back="O(log n) complexity", card_index=0, card_type="Basic")
            card2 = Card(problem_id=problem.id, run_id="run-1", front="Q2", back="Other answer", card_index=1, card_type="Basic")
            session.add_all([card1, card2])

        result = search_cards("log n")

        assert_that(result).is_length(1)
        assert_that(result[0].back).contains("log n")

    def test_search_cards_no_matches(self, in_memory_db):
        """
        Given cards in database
        When search_cards is called with non-matching query
        Then it returns empty list
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            card = Card(problem_id=problem.id, run_id="run-1", front="Q1", back="A1", card_index=0, card_type="Basic")
            session.add(card)

        result = search_cards("nonexistent")

        assert_that(result).is_empty()


class TestGetRunStatistics:
    """Tests for get_run_statistics function."""

    def test_get_run_statistics_valid_run(self, in_memory_db):
        """
        Given a run with problems and cards
        When get_run_statistics is called
        Then it returns statistics dictionary
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed", user_label="test")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success", processing_time_seconds=5.0)
            session.add_all([run, problem])
            session.flush()

            pr = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="cerebras", provider_model="llama-3.1-70b", success=True, card_count=3)
            card1 = Card(problem_id=problem.id, run_id="run-1", front="Q1", back="A1", card_index=0, card_type="Basic")
            card2 = Card(problem_id=problem.id, run_id="run-1", front="Q2", back="A2", card_index=1, card_type="Basic")
            session.add_all([pr, card1, card2])

        result = get_run_statistics("run-1")

        assert_that(result).contains_key("run_id", "total_problems", "total_cards", "success_rate")
        assert_that(result["run_id"]).is_equal_to("run-1")
        assert_that(result["total_problems"]).is_equal_to(1)
        assert_that(result["successful_problems"]).is_equal_to(1)
        assert_that(result["total_cards"]).is_equal_to(2)

    def test_get_run_statistics_invalid_run(self, in_memory_db):
        """
        Given no run with the ID
        When get_run_statistics is called
        Then it returns error dictionary
        """
        result = get_run_statistics("nonexistent-run")

        assert_that(result).contains_key("error")
        assert_that(result["error"]).is_equal_to("Run not found")

    def test_get_run_statistics_with_provider_breakdown(self, in_memory_db):
        """
        Given a run with multiple providers
        When get_run_statistics is called
        Then it includes provider breakdown
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem = Problem(run_id="run-1", question_name="Binary Search", sanitized_name="binary_search", status="success")
            session.add_all([run, problem])
            session.flush()

            pr1 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="cerebras", provider_model="llama-3.1-70b", success=True, card_count=3)
            pr2 = ProviderResult(problem_id=problem.id, run_id="run-1", provider_name="openrouter", provider_model="gpt-4", success=False, card_count=0)
            session.add_all([pr1, pr2])

        result = get_run_statistics("run-1")

        assert_that(result["provider_results"]["by_provider"]).contains_key("cerebras", "openrouter")
        assert_that(result["provider_results"]["by_provider"]["cerebras"]["successful"]).is_equal_to(1)
        assert_that(result["provider_results"]["by_provider"]["openrouter"]["failed"]).is_equal_to(1)


class TestCompareRuns:
    """Tests for compare_runs function."""

    def test_compare_runs_valid_runs(self, in_memory_db):
        """
        Given two valid runs
        When compare_runs is called
        Then it returns comparison dictionary
        """
        with in_memory_db.session_scope() as session:
            run1 = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            run2 = Run(id="run-2", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            problem1 = Problem(run_id="run-1", question_name="Q1", sanitized_name="q1", status="success")
            problem2 = Problem(run_id="run-2", question_name="Q1", sanitized_name="q1", status="success")
            problem3 = Problem(run_id="run-2", question_name="Q2", sanitized_name="q2", status="success")
            session.add_all([run1, run2, problem1, problem2, problem3])
            session.flush()

            card1 = Card(problem_id=problem1.id, run_id="run-1", front="Q", back="A", card_index=0, card_type="Basic")
            card2 = Card(problem_id=problem2.id, run_id="run-2", front="Q", back="A", card_index=0, card_type="Basic")
            card3 = Card(problem_id=problem3.id, run_id="run-2", front="Q2", back="A2", card_index=0, card_type="Basic")
            session.add_all([card1, card2, card3])

        result = compare_runs("run-1", "run-2")

        assert_that(result).contains_key("run1", "run2", "differences")
        assert_that(result["differences"]["total_problems_diff"]).is_equal_to(1)  # run2 has 1 more problem
        assert_that(result["differences"]["total_cards_diff"]).is_equal_to(1)  # run2 has 1 more card

    def test_compare_runs_one_invalid(self, in_memory_db):
        """
        Given one valid and one invalid run
        When compare_runs is called
        Then it returns error dictionary
        """
        with in_memory_db.session_scope() as session:
            run = Run(id="run-1", mode="leetcode", subject="leetcode", card_type="standard", status="completed")
            session.add(run)

        result = compare_runs("run-1", "nonexistent-run")

        assert_that(result).contains_key("error")
        assert_that(result["error"]).is_equal_to("One or both runs not found")

    def test_compare_runs_both_invalid(self, in_memory_db):
        """
        Given two invalid run IDs
        When compare_runs is called
        Then it returns error dictionary
        """
        result = compare_runs("invalid-1", "invalid-2")

        assert_that(result).contains_key("error")
        assert_that(result["error"]).is_equal_to("One or both runs not found")
