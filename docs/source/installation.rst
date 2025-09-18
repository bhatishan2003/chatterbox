Installation
============

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

Prerequisites
-------------

*   Python 3.11 or higher

Steps
-----

1.  **Clone the repository:**

    .. code-block:: bash

        git clone https://github.com/bhatishan2003/chatterbox.git
        cd chatterbox

2.  **Create and activate a virtual environment (recommended):**

    *   **Windows:**

        .. code-block:: bash

            python -m venv .venv
            .venv\Scripts\activate

    *   **macOS & Linux:**

        .. code-block:: bash

            python -m venv .venv
            source .venv/bin/activate

3.  **Install the package:**

    *   For regular use:

        .. code-block:: bash

            pip install .

    *   For development (editable mode):

        .. code-block:: bash

            pip install -e .
