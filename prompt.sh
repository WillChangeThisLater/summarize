#!/bin/bash

set -euo pipefail

reference_links=(
  ""
)

# Function to display references in a readable manner
references() {
  echo "# Reference Index"
  for reference_link in "${reference_links[@]}"; do
    # Print a header with Markdown style
    echo -e "\n## Reference: $reference_link\n"
    lynx -dump -nolist "$reference_link"
    echo -e "\n"
  done
}

about() {
    cat <<EOF

Directory structure
$(tree)

Files
$(files-to-prompt . --ignore prompt.sh)

EOF
}

run() {

    echo "$@" >&2

    echo "\`\`\`bash"
    echo "\$ $@"
    $@ 2>&1
    echo "\`\`\`"
}

main() {
  cat <<EOF
About:
$(about)

References:
$(references)

I am building a CLI tool called 'summarize'.
I want the tool to take in URIs from stdin
(newline delimited), dispatch to an appropriate
handler, and use that handler to summarize
the content of each URI.

Code should be async as much as possible, with
semaphores to manage concurrency limits.

On a high level, the flow should be very similar
to another project I have, 'filter'. There should
be some kind of main CLI script which defines the
CLI interface and dispatches to the appropriate method.
On the backend, different clients should be set up
that can call out to backend LLM providers like openai
and bedrock.

'summarize' should be able to handle text and image files,
web URLs, and links to confluence pages and JIRA tickets

You should be able to steal a significant amount of code
from an existing project I maintain, 'filter'. Relevant
snippets of code are below:

\`\`\`filter/main.py
$(cat -n /home/arch/filter/src/filter/main.py)
\`\`\`

\`\`\`filter/decorators.py
$(cat -n /home/arch/filter/src/filter/decorators.py)
\`\`\`

\`\`\`filter/clients/base.py
$(cat -n /home/arch/filter/src/filter/clients/base.py)
\`\`\`

\`\`\`filter/clients/bedrock.py
$(cat -n /home/arch/filter/src/filter/clients/bedrock.py)
\`\`\`

\`\`\`filter/clients/openai.py
$(cat -n /home/arch/filter/src/filter/clients/openai.py)
\`\`\`

I want the LLM clients to return summaries via structured outputs.
I have a rough draft below:

\`\`\`json
{
  "author": str | None, # author, if one can be found
  "publish_date": str | None, # %Y-%m-%d format
  "content_type": str, # text, json, image, etc.
  "language": str, # language
  "tags": list[str], # free-form tags
  "summary": str, # summary of the content
}

Create a summarization prompt in the bedrock client. This should direct
the client to summarize content in this format. It should also provide
a short example illustrating how to do this.
\`\`\`


EOF
}

main
