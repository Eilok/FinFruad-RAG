param(
  [int]$TestLimit = 500,
  [int]$TrainPositiveLimit = 0,
  [int]$KeywordTopK = 3,
  [int]$VectorTopK = 3,
  [string]$CollectionName = ""
)

$cmd = "uv run python -m backend.scripts.run_eval --test-limit $TestLimit --train-positive-limit $TrainPositiveLimit --keyword-top-k $KeywordTopK --vector-top-k $VectorTopK"
if ($CollectionName -ne "") {
  $cmd = "$cmd --collection-name $CollectionName"
}
Invoke-Expression $cmd
