# Adopts the repo, which existed before infra/github did, into this state
# (ADR 006 in todofixthis/terraform-github-repository). Delete this file in a
# follow-up PR once applied: left in, a module release that renames one of
# these addresses fails the plan.
import {
  id = "filters-pydantic"
  to = module.repository.github_branch_default.this
}

import {
  id = "filters-pydantic"
  to = module.repository.github_repository.this
}

import {
  id = "filters-pydantic"
  to = module.repository.github_repository_dependabot_security_updates.this
}

import {
  id = "filters-pydantic"
  to = module.repository.github_repository_vulnerability_alerts.this
}

# The hand-made develop ruleset, rewritten in place to the module's
import {
  id = "filters-pydantic:24623929"
  to = module.repository.github_repository_ruleset.trunk["develop"]
}

# The hand-made main ruleset, rewritten in place to the module's
import {
  id = "filters-pydantic:24623933"
  to = module.repository.github_repository_ruleset.trunk["main"]
}
