import os
import json
import time
from datetime import datetime
import anthropic
from exa_py import Exa
from firecrawl import FirecrawlApp
import streamlit as st


class AgenticResearcher:

    def __init__(self,
                 anthropic_api_key,
                 exa_api_key,
                 firecrawl_api_key,
                 model="claude-3-5-sonnet-latest",
                 results_per_search=5,
                 progress_callback=None):
        self.claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.exa_client = Exa(api_key=exa_api_key)
        self.firecrawl_client = FirecrawlApp(api_key=firecrawl_api_key)
        self.messages = []
        self.model = model
        self.progress_callback = progress_callback

        # Get current date for system prompt
        current_date = datetime.now().strftime("%A, %B %d, %Y")

        self.system_prompt = f"""You are a research assistant specializing in scientific literature analysis.
        Your task is to thoroughly research topics through multiple iterations, analyzing search results,
        identifying knowledge gaps, and formulating follow-up queries to deepen understanding.

        Today's date is {current_date}.

        You have two tools at your disposal:
        1. web_search - Use this to find scientific papers on a topic, along with some of their contents.
           You can specify date ranges for your searches when needed, but only add dates if truly needed for the search.
        2. get_full_content - Use this to retrieve the full content in Markdown of a specific article when search results contain promising articles that require deeper analysis.

        Always analyze sources critically.
        """

        self.research_iterations = []
        self.search_history = []
        self.content_retrieval_history = []
        self.results_per_search = results_per_search

    def update_progress(self,
                        message,
                        progress_type="info",
                        iteration_num=None,
                        total_iterations=None):
        """Update progress in Streamlit UI"""
        if self.progress_callback:
            self.progress_callback(message, progress_type, iteration_num,
                                   total_iterations)

    def search_with_exa(self,
                        query,
                        num_results=None,
                        start_date=None,
                        end_date=None):
        """Perform a search for scientific papers using Exa API with optional date range"""
        if num_results is None:
            num_results = self.results_per_search

        self.update_progress(f"Searching for: {query}", "search")

        try:
            # Prepare search parameters
            search_params = {
                "query": query,
                "type": "keyword",
                "category": "research paper",
                "num_results": num_results,
                "text": {
                    "max_characters": 5000
                }
            }

            # Only add date parameters if they're actually provided
            if start_date:
                search_params["start_published_date"] = start_date

            if end_date:
                search_params["end_published_date"] = end_date

            # Execute the search with only the necessary parameters
            results = self.exa_client.search_and_contents(**search_params)

            # Log the search with timestamp
            current_time = datetime.now().isoformat()
            result_count = 0

            # Safely count results
            if hasattr(results, 'results'):
                result_count = len(results.results)
            elif isinstance(results, dict) and 'results' in results:
                result_count = len(results['results'])

            self.search_history.append({
                "query": query,
                "timestamp": current_time,
                "num_results": result_count,
                "start_date": start_date,
                "end_date": end_date
            })

            self.update_progress(f"Found {result_count} results for '{query}'",
                                 "search")
            return results
        except Exception as e:
            self.update_progress(f"Search error: {str(e)}", "error")
            # Add failed search to history
            self.search_history.append({
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "num_results": 0,
                "start_date": start_date,
                "end_date": end_date
            })
            return None

    def get_full_content(self, url):
        """Get the full content of an article using Firecrawl"""
        self.update_progress(f"Retrieving content from: {url}", "content")

        try:
            # Updated to match current Firecrawl API
            response = self.firecrawl_client.scrape_url(
                url,
                formats=['markdown']  # Pass formats directly, not in params
            )

            # Handle ScrapeResponse object
            content = "Error retrieving content"

            # Try different ways to access the markdown content
            if hasattr(response, 'markdown'):
                # Direct attribute access
                content = response.markdown
            elif hasattr(response, 'data'):
                # Response might have a data attribute
                if hasattr(response.data, 'markdown'):
                    content = response.data.markdown
                elif isinstance(response.data,
                                dict) and 'markdown' in response.data:
                    content = response.data['markdown']
            elif isinstance(response, dict):
                # In case it's a dictionary
                if 'data' in response and isinstance(response['data'], dict):
                    content = response['data'].get('markdown',
                                                   'Error retrieving content')
                else:
                    content = response.get('markdown',
                                           'Error retrieving content')

            # Log the content retrieval
            self.content_retrieval_history.append({
                "url":
                url,
                "timestamp":
                datetime.now().isoformat(),
                "success":
                True if content != "Error retrieving content" else False,
                "content_length":
                len(content)
            })

            self.update_progress(
                f"Retrieved {len(content)} characters from article", "content")
            return content[:100000]
        except Exception as e:
            self.update_progress(f"Content retrieval error: {str(e)}", "error")

            # Log the failed retrieval
            self.content_retrieval_history.append({
                "url":
                url,
                "timestamp":
                datetime.now().isoformat(),
                "success":
                False,
                "error":
                str(e)
            })

            return "Error retrieving content"

    def initialize_conversation(self, user_query):
        """Set up the initial conversation with Claude"""
        self.messages = [{
            "role":
            "user",
            "content":
            f"I want to thoroughly research: '{user_query}'. Please search for relevant scientific literature on this topic."
        }]

    def format_search_results(self, search_response):
        """Format search results into a readable string"""
        if search_response is None:
            return "No search results found."

        formatted = []
        results = []

        # Safely access the results from the Exa response object
        try:
            if hasattr(search_response, 'results'):
                results = search_response.results
            elif isinstance(search_response,
                            dict) and 'results' in search_response:
                results = search_response['results']
            else:
                self.update_progress("Unexpected search response format",
                                     "error")
        except Exception as e:
            self.update_progress(f"Error processing search response: {str(e)}",
                                 "error")
            return "Error processing search results."

        for idx, result in enumerate(results):
            try:
                article_text = f"--- Article {idx+1} ---\n"

                # Handle different potential result formats
                if isinstance(result, dict):
                    article_text += f"Title: {result.get('title', 'N/A')}\n"
                    article_text += f"URL: {result.get('url', 'N/A')}\n"
                    article_text += f"Published: {result.get('publishedDate', 'N/A')}\n"
                    article_text += f"Author: {result.get('author', 'N/A')}\n"

                    if 'text' in result:
                        content = result['text'][:2000] + "..." if len(
                            result['text']) > 2000 else result['text']
                        article_text += f"Content excerpt:\n{content}\n\n"
                else:
                    # Assume it's an object with attributes
                    article_text += f"Title: {getattr(result, 'title', 'N/A')}\n"
                    article_text += f"URL: {getattr(result, 'url', 'N/A')}\n"
                    article_text += f"Published: {getattr(result, 'publishedDate', 'N/A')}\n"
                    article_text += f"Author: {getattr(result, 'author', 'N/A')}\n"

                    if hasattr(result, 'text'):
                        content = result.text[:2000] + "..." if len(
                            result.text) > 2000 else result.text
                        article_text += f"Content excerpt:\n{content}\n\n"

                formatted.append(article_text)
            except Exception as e:
                formatted.append(
                    f"--- Article {idx+1} ---\n[Error formatting this result]\n\n"
                )

        if not formatted:
            return "No results found for the given query."

        return "\n".join(formatted)

    def extract_text_content(self, content_list):
        """Extract text content from Claude's response"""
        try:
            text_content = []
            for item in content_list:
                if hasattr(item, 'type') and item.type == "text":
                    text_content.append(item.text)
            return "\n".join(text_content)
        except Exception as e:
            self.update_progress(f"Failed to extract text content: {str(e)}",
                                 "error")
            return "Error extracting content from Claude's response"

    def run_research_iteration(self):
        """Run a single iteration of research with Claude"""
        try:
            self.update_progress("Requesting Claude's analysis...", "info")
            response = self.claude_client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=self.system_prompt,
                messages=self.messages,
                tools=[{
                    "name": "web_search",
                    "description":
                    "Search for scientific papers and articles with optional date filtering",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type":
                                "string",
                                "description":
                                "The search query. Should ideally be under 5 words."
                            },
                            "start_date": {
                                "type":
                                "string",
                                "description":
                                "Optional start date in ISO format (YYYY-MM-DDTHH:MM:SS.SSSZ)"
                            },
                            "end_date": {
                                "type":
                                "string",
                                "description":
                                "Optional end date in ISO format (YYYY-MM-DDTHH:MM:SS.SSSZ)"
                            }
                        },
                        "required": ["query"]
                    }
                }, {
                    "name": "get_article_content",
                    "description":
                    "Retrieve the full content of a scientific article by URL",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description":
                                "The URL of the article to retrieve"
                            }
                        },
                        "required": ["url"]
                    }
                }])

            # Check if the response is using a tool
            tool_use_detected = False
            claude_initial_response = self.extract_text_content(
                response.content)

            # Update progress with Claude's initial response
            self.update_progress("Claude is analyzing the research topic...",
                                 "info")

            for content_item in response.content:
                if hasattr(content_item,
                           'type') and content_item.type == "tool_use":
                    # Handle web_search tool use
                    if content_item.name == "web_search":
                        tool_use_detected = True
                        search_query = content_item.input.get("query", "")
                        start_date = content_item.input.get("start_date", None)
                        end_date = content_item.input.get("end_date", None)
                        tool_use_id = content_item.id

                        date_range_str = ""
                        if start_date or end_date:
                            date_range_str = f" with date range: {start_date or 'any'} to {end_date or 'present'}"

                        self.update_progress(
                            f"Claude is searching for: '{search_query}'{date_range_str}",
                            "search")

                        # Add the assistant's response to the conversation
                        self.messages.append({
                            "role": "assistant",
                            "content": response.content
                        })

                        # Execute the search with date parameters if provided
                        search_results = self.search_with_exa(
                            search_query,
                            start_date=start_date,
                            end_date=end_date)

                        # Format the results
                        formatted_results = self.format_search_results(
                            search_results)

                        # Update progress with results summary
                        result_count = 0
                        if search_results:
                            if hasattr(search_results, 'results'):
                                result_count = len(search_results.results)
                            elif isinstance(
                                    search_results,
                                    dict) and 'results' in search_results:
                                result_count = len(search_results['results'])

                        self.update_progress(
                            f"Found {result_count} papers. Claude is analyzing...",
                            "info")

                        # Add the search results to the conversation
                        self.messages.append({
                            "role":
                            "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": formatted_results
                            }]
                        })

                        # Get Claude's analysis of the search results
                        self.update_progress(
                            "Claude is analyzing search results...", "info")
                        analysis_response = self.claude_client.messages.create(
                            model=self.model,
                            max_tokens=4000,
                            system=self.system_prompt,
                            messages=self.messages)

                        # Extract the analysis text
                        analysis_text = self.extract_text_content(
                            analysis_response.content)

                        # Add Claude's analysis to the conversation
                        self.messages.append({
                            "role":
                            "assistant",
                            "content":
                            analysis_response.content
                        })

                        # Return the text content of Claude's analysis
                        return analysis_text

                    # Handle get_article_content tool use
                    elif content_item.name == "get_article_content":
                        tool_use_detected = True
                        article_url = content_item.input.get("url", "")
                        tool_use_id = content_item.id

                        self.update_progress(
                            f"Claude is retrieving full article content...",
                            "content")

                        # Add the assistant's response to the conversation
                        self.messages.append({
                            "role": "assistant",
                            "content": response.content
                        })

                        # Execute the content retrieval
                        article_content = self.get_full_content(article_url)

                        self.update_progress(
                            "Article retrieved. Claude is analyzing...",
                            "info")

                        # Add the content to the conversation
                        self.messages.append({
                            "role":
                            "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": article_content
                            }]
                        })

                        # Get Claude's analysis of the article content
                        self.update_progress(
                            "Claude is analyzing article content...", "info")
                        analysis_response = self.claude_client.messages.create(
                            model=self.model,
                            max_tokens=4000,
                            system=self.system_prompt,
                            messages=self.messages)

                        # Extract the analysis text
                        analysis_text = self.extract_text_content(
                            analysis_response.content)

                        # Add Claude's analysis to the conversation
                        self.messages.append({
                            "role":
                            "assistant",
                            "content":
                            analysis_response.content
                        })

                        # Return the text content of Claude's analysis
                        return analysis_text

            # If no tool use was detected
            if not tool_use_detected:
                self.update_progress(
                    "Claude is formulating research strategy...", "info")
                self.messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                return claude_initial_response

        except Exception as e:
            self.update_progress(f"Error during research iteration: {str(e)}",
                                 "error")
            import traceback
            traceback.print_exc()
            return f"An error occurred: {e}"

    def run_research_loop(self, user_query, max_iterations=10):
        """Run the complete research loop with multiple iterations"""
        self.update_progress(f"Starting research on: '{user_query}'", "info")
        self.update_progress(f"Planning {max_iterations} research iterations",
                             "info")

        self.initialize_conversation(user_query)

        for i in range(max_iterations):
            # Send iteration number directly - no parsing needed!
            self.update_progress(f"Research iteration {i+1}/{max_iterations}",
                                 "iteration", i + 1, max_iterations)

            # Run the research iteration
            claude_response = self.run_research_iteration()
            current_time = datetime.now().isoformat()

            # Find all searches performed during this iteration
            if i == 0:
                # For the first iteration, get all searches so far
                iteration_searches = self.search_history.copy()
                iteration_content_retrievals = self.content_retrieval_history.copy(
                )
            else:
                # For subsequent iterations, get searches since the last iteration timestamp
                last_iteration_time = self.research_iterations[-1]["timestamp"]
                iteration_searches = [
                    s for s in self.search_history
                    if s["timestamp"] > last_iteration_time
                ]
                iteration_content_retrievals = [
                    c for c in self.content_retrieval_history
                    if c["timestamp"] > last_iteration_time
                ]

            # Store the full iteration with timestamp
            self.research_iterations.append({
                "iteration": i + 1,
                "query": user_query,
                "response": claude_response,
                "search_queries": iteration_searches,
                "content_retrievals": iteration_content_retrievals,
                "timestamp": current_time
            })

            # If not the last iteration, prompt for next search
            if i < max_iterations - 1:
                next_prompt = f"""
                Based on what you've learned so far about {user_query}, please:

                1. Identify a key gap in our current understanding
                2. Formulate a specific follow-up search query to address this gap or retrieve a full article if needed
                   (You can specify date ranges for your search if relevant)
                3. Execute the search or content retrieval and analyze the results
                """

                self.messages.append({"role": "user", "content": next_prompt})

        # Generate final synthesis
        self.update_progress("Generating comprehensive research report...",
                             "final_report")

        final_prompt = f"""
        We've completed {max_iterations} iterations of research on "{user_query}".

        Please synthesize all the information you've gathered into a lengthy comprehensive research report (at least five pages).
        This should not be a summary but rather a comprehensive literature review.

        You must include proper citations to the sources you've used.

        Your report should:
        1. Have a clear introduction stating the research question
        2. Organize findings into logical sections with headings
        3. Provide detailed, lengthy descriptions about the current state of knowledge with numbers, evidence, and quotes from papers
        4. Identify remaining questions or areas for future research
        5. Conclude with key takeaways
        6. Have a complete untruncated references list
        7. Be in Markdown format with all sources linked using something like [source](link)
        """

        self.messages.append({"role": "user", "content": final_prompt})

        try:
            final_report_response = self.claude_client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=self.system_prompt,
                messages=self.messages)

            final_report = self.extract_text_content(
                final_report_response.content)

            # Store all research data with timestamp
            research_data = {
                "query": user_query,
                "model": self.model,
                "iterations": self.research_iterations,
                "search_history": self.search_history,
                "content_retrieval_history": self.content_retrieval_history,
                "final_report": final_report,
                "timestamp": datetime.now().isoformat()
            }

            self.update_progress("Research complete!", "info")
            return final_report, research_data

        except Exception as e:
            self.update_progress(f"Error generating final report: {str(e)}",
                                 "error")
            import traceback
            traceback.print_exc()
            return f"An error occurred while generating the final report: {e}", {
                "query": user_query,
                "iterations": self.research_iterations,
                "search_history": self.search_history,
                "content_retrieval_history": self.content_retrieval_history,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
